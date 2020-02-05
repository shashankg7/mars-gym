from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, Union

import gym
import luigi
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch.utils.data.dataloader import DataLoader
from torchbearer import Trial

from recommendation.gym_ifood.envs import IFoodRecSysEnv
from recommendation.model.bandit import BanditPolicy, BANDIT_POLICIES
from recommendation.task.data_preparation.ifood import CreateGroundTruthForInterativeEvaluation, \
    GenerateIndicesForAccountsAndMerchantsDataset, AddAdditionallInformationDataset
from recommendation.task.model.contextual_bandits import ContextualBanditsTraining
from recommendation.torch import NoAutoCollationDataLoader
from recommendation.utils import get_scores_per_tuples_with_click_timestamp


class BanditAgent(object):

    def __init__(self, bandit: BanditPolicy) -> None:
        super().__init__()

        self.bandit = bandit

    def fit(self, trial: Trial, train_loader: DataLoader, val_loader: DataLoader, epochs: int):
        trial.with_generators(train_generator=train_loader, val_generator=val_loader).run(epochs=epochs)

        self.bandit.fit(train_loader.dataset)

    def act(self, batch_of_arm_indices: List[List[int]], batch_of_arm_scores: List[List[float]]) -> np.ndarray:
        return np.array([self.bandit.select_idx(arm_indices, arm_scores=arm_scores)
                         for arm_indices, arm_scores in zip(batch_of_arm_indices, batch_of_arm_scores)])


class IteractionTraining(ContextualBanditsTraining):
    project = "ifood_contextual_bandit"
    test_size = 0.0

    obs_batch_size: int = luigi.IntParameter(default=2000)
    filter_dish: str = luigi.Parameter(default="all")

    num_episodes: int = luigi.IntParameter(default=1)
    full_refit: bool = luigi.BoolParameter(default=False)

    bandit_policy: str = luigi.ChoiceParameter(choices=BANDIT_POLICIES.keys(), default="model")
    bandit_policy_params: Dict[str, Any] = luigi.DictParameter(default={})

    def requires(self):
        return CreateGroundTruthForInterativeEvaluation(minimum_interactions=self.minimum_interactions,
                                                        filter_dish=self.filter_dish), \
               GenerateIndicesForAccountsAndMerchantsDataset(
                   test_size=self.test_size,
                   minimum_interactions=self.minimum_interactions,
                   sample_size=self.sample_size), \
               AddAdditionallInformationDataset(
                   test_size=self.test_size,
                   sample_size=self.sample_size,
                   minimum_interactions=self.minimum_interactions)

    def create_agent(self) -> BanditAgent:
        bandit = BANDIT_POLICIES[self.bandit_policy](reward_model=self.create_module(), **self.bandit_policy_params)
        return BanditAgent(bandit)

    @property
    def metadata_data_frame_path(self) -> str:
        return self.input()[1][1].path

    @property
    def account_data_frame(self) -> pd.DataFrame:
        if not hasattr(self, "_account_data_frame"):
            self._account_data_frame = pd.read_csv(self.input()[1][0].path)

        return self._account_data_frame

    @property
    def merchant_data_frame(self) -> pd.DataFrame:
        if not hasattr(self, "_merchant_data_frame"):
            self._merchant_data_frame = pd.read_csv(self.input()[1][1].path)

        return self._merchant_data_frame

    @property
    def availability_data_frame(self) -> pd.DataFrame:
        if not hasattr(self, "_availability_data_frame"):
            df = pd.read_parquet(self.input()[2][1].path)
            df = df.merge(self.merchant_data_frame[["merchant_id", "merchant_idx"]], on="merchant_id")
            df["open_time"] = df["open"].apply(datetime.time)
            df["close_time"] = df["close"].apply(datetime.time)
            df["open_time_minus_30_min"] = df["open"].apply(lambda dt: datetime.time(dt - timedelta(minutes=30)))
            df["close_time_plus_30_min"] = df["close"].apply(lambda dt: datetime.time(dt + timedelta(minutes=30)))

            self._availability_data_frame = df

        return self._availability_data_frame

    def _get_batch_of_arm_indices(self, ob: np.ndarray) -> List[List[int]]:
        df = self.availability_data_frame
        days_of_week = [int(click_timestamp.strftime('%w')) for click_timestamp in ob[:, 1]]
        click_times = [datetime.time(click_timestamp) for click_timestamp in ob[:, 1]]
        return [
            df[
                (df["day_of_week"] == day_of_week) &
                ((df["open_time_minus_30_min"] <= click_time) | (df["open_time"] <= click_time)) &
                ((df["close_time_plus_30_min"] >= click_time) | (df["close_time"] >= click_time))
                ]["merchant_idx"].values.tolist()
            for click_time, day_of_week in zip(click_times, days_of_week)
        ]

    def _get_scores_from_reward_model(self, agent: BanditAgent, ob: np.ndarray,
                                      batch_of_arm_indices: List[List[int]]) -> Dict[Tuple[int, int, datetime], float]:
        tuples_df = pd.DataFrame(columns=["account_idx", "merchant_idx", "click_timestamp"],
                                 data=[(account_idx, merchant_idx, click_timestamp)
                                       for account_idx, merchant_idx_list, click_timestamp
                                       in zip(ob[:, 0], batch_of_arm_indices, ob[:, 1])
                                       for merchant_idx in merchant_idx_list])

        def _get_hist_visits(row: pd.Series) -> int:
            try:
                return len(
                    self.known_observations_data_frame.loc[row["account_idx"], row["merchant_idx"],
                    :row["click_timestamp"]])
            except KeyError:
                return 0

        def _get_hist_buys(row: pd.Series) -> int:
            try:
                return self.known_observations_data_frame.loc[row["account_idx"], row["merchant_idx"],
                       :row["click_timestamp"]]["buy"].sum()
            except KeyError:
                return 0

        tuples_df["hist_visits"] = tuples_df.apply(_get_hist_visits, axis=1)
        tuples_df["hist_buys"] = tuples_df.apply(_get_hist_buys, axis=1)

        if self.project_config.output_column.name not in tuples_df.columns:
            tuples_df[self.project_config.output_column.name] = 1
        for auxiliar_output_column in self.project_config.auxiliar_output_columns:
            if auxiliar_output_column.name not in tuples_df.columns:
                tuples_df[auxiliar_output_column.name] = 0
        dataset = self.project_config.dataset_class(tuples_df, self.metadata_data_frame, self.project_config,
                                                    negative_proportion=0.0)
        generator = NoAutoCollationDataLoader(
            dataset, batch_size=self.batch_size, shuffle=False,
            num_workers=self.generator_workers,
            pin_memory=self.pin_memory if self.device == "cuda" else False)
        trial = Trial(agent.bandit.reward_model, criterion=lambda *args: torch.zeros(1, device=self.torch_device,
                                                                                     requires_grad=True)) \
            .with_test_generator(generator).to(self.torch_device).eval()
        with torch.no_grad():
            model_output: Union[torch.Tensor, Tuple[torch.Tensor]] = trial.predict(verbose=2)
        scores_tensor: torch.Tensor = model_output if isinstance(model_output, torch.Tensor) else model_output[0][0]
        scores: np.ndarray = scores_tensor.cpu().numpy()
        return {
            (account_idx, merchant_idx, click_timestamp): score
            for account_idx, merchant_idx, click_timestamp, score in
            zip(tuples_df["account_idx"], tuples_df["merchant_idx"],
                tuples_df["click_timestamp"], scores)
        }

    def _get_batch_of_arm_scores(self, agent: BanditAgent, ob: np.ndarray,
                                 arm_indices: List[List[int]]) -> List[List[float]]:
        scores_per_tuple = self._get_scores_from_reward_model(agent, ob, arm_indices)
        return [get_scores_per_tuples_with_click_timestamp(account_idx, merchant_idx_list, click_timestamp,
                                                           scores_per_tuple)
                for account_idx, merchant_idx_list, click_timestamp in zip(ob[:, 0], arm_indices, ob[:, 1])]

    def _create_arm_contexts(self, ob: np.ndarray) -> List[Tuple[np.ndarray, ...]]:
        pass

    @property
    def known_observations_data_frame(self) -> pd.DataFrame:
        if not hasattr(self, "_known_observations_data_frame"):
            df = pd.DataFrame(columns=["account_idx", "merchant_idx", "click_timestamp", "buy"])
            df = df.astype({
                "account_idx": np.int,
                "merchant_idx": np.int,
                "click_timestamp": np.datetime64,
                "buy": np.int,
            })
            df = df.set_index(["account_idx", "merchant_idx", "click_timestamp"], drop=False).sort_index()
            df.index.set_names(["index_account_idx", "index_merchant_idx", "index_click_timestamp"], inplace=True)
            self._known_observations_data_frame = df
        return self._known_observations_data_frame

    def _accumulate_known_observations(self, ob: np.ndarray, action: np.ndarray, reward: np.ndarray):
        df = self.known_observations_data_frame
        df = pd.concat([df, pd.DataFrame(columns=["account_idx", "merchant_idx", "click_timestamp", "buy"],
                         data={"account_idx": ob[:, 0], "merchant_idx": action, "click_timestamp": ob[:, 1],
                               "buy": reward})]).sort_index()
        df["hist_visits"] = 1
        df["hist_visits"] = df.groupby(["account_idx", "merchant_idx"])["hist_visits"].transform("cumsum")
        df["hist_buys"] = df.groupby(["account_idx", "merchant_idx"])["buy"].transform("cumsum")

        df["ps"] = 1.0  # TODO: Calculate the PS

        self._known_observations_data_frame = df

    @property
    def train_data_frame(self) -> pd.DataFrame:
        return self._train_data_frame

    @property
    def val_data_frame(self) -> pd.DataFrame:
        return self._val_data_frame

    @property
    def test_data_frame(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _reset_dataset(self):
        self._train_data_frame, self._val_data_frame = train_test_split(
            self.known_observations_data_frame, test_size=self.val_size, random_state=self.seed)
        if hasattr(self, "_train_dataset"):
            del self._train_dataset
        if hasattr(self, "_val_dataset"):
            del self._val_dataset

    @property
    def n_users(self) -> int:
        if not hasattr(self, "_n_users"):
            self._n_users = len(self.account_data_frame)
        return self._n_users

    @property
    def n_items(self) -> int:
        if not hasattr(self, "_n_items"):
            self._n_items = len(self.merchant_data_frame)
        return self._n_items

    def run(self):
        self.ground_truth_data_frame = pd.read_parquet(self.input()[0].path)
        env: IFoodRecSysEnv = gym.make('ifood-recsys-v0', dataset=self.ground_truth_data_frame,
                                       obs_batch_size=self.obs_batch_size)

        env.seed(0)

        agent: BanditAgent = None
        if not self.full_refit:
            agent = self.create_agent()

        rewards = []
        interactions = 0
        done = False

        for i in range(self.num_episodes):
            ob = env.reset()
            while True:
                interactions += len(ob)

                if self.full_refit:
                    agent = self.create_agent()

                batch_of_arm_indices = self._get_batch_of_arm_indices(ob)
                batch_of_arm_scores = self._get_batch_of_arm_scores(agent, ob, batch_of_arm_indices) \
                    if agent.bandit.reward_model else [True for _ in range(len(batch_of_arm_indices))]
                action = agent.act(batch_of_arm_indices, batch_of_arm_scores)
                new_ob, reward, done, info = env.step(action)
                rewards.append(reward)
                if done:
                    break

                self._accumulate_known_observations(ob, action, reward)
                ob = new_ob
                self._reset_dataset()
                if agent.bandit.reward_model:
                    agent.fit(self.create_trial(agent.bandit.reward_model), self.get_train_generator(),
                              self.get_val_generator(), self.epochs)

                print(interactions)
                print(np.mean(reward), np.std(reward))

        env.close()
