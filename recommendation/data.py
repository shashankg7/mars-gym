import abc
import ast
from typing import Tuple, List, Iterator, Union, Sized, Callable

import torch
from torch.utils.data import Dataset
import pandas as pd
import numpy as np
from scipy.sparse.csr import csr_matrix

from recommendation.task.meta_config import ProjectConfig, IOType, RecommenderType
from recommendation.torch import coo_matrix_to_sparse_tensor


class CorruptionTransformation(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, seed: int = 42) -> None:
        self._random_state = np.random.RandomState(seed)

    def setup(self, data: csr_matrix):
        pass

    @abc.abstractmethod
    def __call__(self, data: csr_matrix) -> csr_matrix:
        pass


class SupportBasedCorruptionTransformation(CorruptionTransformation):
    def setup(self, data: csr_matrix):
        self._supports = np.asarray(data.astype(bool).sum(axis=0)).flatten() / data.shape[0]

    def __call__(self, data: csr_matrix) -> csr_matrix:
        u = self._random_state.uniform(0, 1, len(data.indices))
        support: np.ndarray = self._supports[data.indices]
        # Normalize
        support = support / support.sum()

        removed_indices = data.indices[u < support]

        if len(removed_indices) == 0 or len(removed_indices) == len(data.indices):
            return data

        data = data.copy()
        data[0, removed_indices] = 0
        data.eliminate_zeros()

        return data


class MaskingNoiseCorruptionTransformation(CorruptionTransformation):
    def __init__(self, fraction: float = 0.25, seed: int = 42) -> None:
        super().__init__(seed)
        self.fraction = fraction

    def __call__(self, data: csr_matrix) -> csr_matrix:
        n = len(data.indices)
        removed_indices = self._random_state.choice(data.indices, round(self.fraction * n), replace=False)

        if len(removed_indices) == 0:
            return data

        data = data.copy()
        data[0, removed_indices] = 0
        data.eliminate_zeros()

        return data


class SaltAndPepperNoiseCorruptionTransformation(CorruptionTransformation):
    def __init__(self, fraction: float = 0.25, seed: int = 42) -> None:
        super().__init__(seed)
        self.fraction = fraction

    def __call__(self, data: csr_matrix) -> csr_matrix:
        removed_indices = self._random_state.choice(data.indices, round(self.fraction * len(data.indices)),
                                                    replace=False)
        removed_indices = removed_indices[self._random_state.uniform(0, 1, len(removed_indices)) > 0.5]

        if len(removed_indices) == 0:
            return data

        data = data.copy()
        data[0, removed_indices] = 0
        data.eliminate_zeros()

        return data


class CriteoDataset(Dataset):
    def __init__(self, data_frame: pd.DataFrame, project_config: ProjectConfig,
                 transformation: Union[Callable] = None) -> None:

        self._data_frame = data_frame

        self._dense_columns = ['I1', 'I2', 'I3', 'I4', 'I5', 'I6', 'I7', 'I8', 'I9', 'I10', 'I11', 'I12', 'I13']
        self._categorical_columns = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11', 'C12', 'C13',
                                     'C14',
                                     'C15', 'C16', 'C17', 'C18', 'C19', 'C20', 'C21', 'C22', 'C23', 'C24', 'C25', 'C26']

        self._input_columns = [input_column.name for input_column in project_config.input_columns]
        self._output_column = project_config.output_column.name
        self._train = True

    def __len__(self) -> int:
        return self._data_frame.shape[0]

    def __getitem__(self, indices: Union[int, List[int]]) -> Tuple[Tuple[np.ndarray, np.ndarray], np.ndarray]:
        if isinstance(indices, int):
            indices = [indices]
        rows: pd.Series = self._data_frame.iloc[indices]


        rows_dense      = rows[self._dense_columns].values#)#.astype(float)
        rows_categories = rows[self._categorical_columns].values#)#.astype(float)

        if self._train:
            return (rows_dense, rows_categories), torch.FloatTensor(rows[self._output_column].values)
        else:
            return (rows_dense, rows_categories)

class InteractionsDataset(Dataset):
    def __init__(self, data_frame: pd.DataFrame, project_config: ProjectConfig,
                 transformation: Union[Callable] = None) -> None:
        assert len(project_config.input_columns) >= 2
        assert all(input_column.type == IOType.INDEX for input_column in project_config.input_columns)

        self._data_frame = data_frame
        self._input_columns = [input_column.name for input_column in project_config.input_columns]
        self._output_column = project_config.output_column.name

    def __len__(self) -> int:
        return self._data_frame.shape[0]

    def __getitem__(self, indices: Union[int, List[int]]) -> Tuple[Tuple[np.ndarray, np.ndarray], np.ndarray]:
        if isinstance(indices, int):
            indices = [indices]
        rows: pd.Series = self._data_frame.iloc[indices]
        return (rows[self._input_columns[0]].values,
                rows[self._input_columns[1]].values), rows[self._output_column].values


class InteractionsMatrixDataset(Dataset):
    def __init__(self, data_frame: pd.DataFrame, project_config: ProjectConfig,
                 transformation: Union[CorruptionTransformation, Callable] = None) -> None:
        assert len(project_config.input_columns) == 1
        assert project_config.input_columns[0].name == project_config.output_column.name

        self._n_users: int = data_frame.iloc[0][project_config.n_users_column]
        self._n_items: int = data_frame.iloc[0][project_config.n_items_column]
        dim = self._n_items if project_config.recommender_type == RecommenderType.USER_BASED_COLLABORATIVE_FILTERING \
            else self._n_users

        target_col = project_config.output_column.name
        if type(data_frame.iloc[0][target_col]) is str:
            data_frame[target_col] = data_frame[target_col].apply(lambda value: ast.literal_eval(value))

        i, j, data = zip(
            *((index, int(t[0]), t[1]) for index, row in enumerate(data_frame[target_col])
              for t in row))
        self._data = csr_matrix((data, (i, j)), shape=(max(i) + 1, dim))

        if isinstance(transformation, CorruptionTransformation):
            transformation.setup(self._data)
        self._transformation = transformation

    def __len__(self) -> int:
        return self._data.shape[0]

    def __getitem__(self, indices: Union[int, List[int]]) -> Tuple[torch.Tensor, torch.Tensor]:
        if isinstance(indices, int):
            indices = [indices]
        rows: csr_matrix = self._data[indices]

        if self._transformation:
            input_rows = self._transformation(rows)
            return coo_matrix_to_sparse_tensor(input_rows.tocoo()), coo_matrix_to_sparse_tensor(rows.tocoo())
        return (coo_matrix_to_sparse_tensor(rows.tocoo()),) * 2


class BinaryInteractionsWithOnlineRandomNegativeGenerationDataset(InteractionsDataset):

    def __init__(self, data_frame: pd.DataFrame, project_config: ProjectConfig,
                 transformation: Union[Callable] = None) -> None:
        data_frame = data_frame[data_frame[project_config.output_column.name] > 0]
        super().__init__(data_frame, project_config, transformation)
        self._non_zero_indices = set(
            data_frame[[self._input_columns[0], self._input_columns[0]]].itertuples(index=False, name=None))

        self._n_users: int = data_frame.iloc[0][project_config.n_users_column]
        self._n_items: int = data_frame.iloc[0][project_config.n_items_column]

    def __len__(self) -> int:
        return super().__len__() * 2

    def _generate_negative_indices(self) -> Tuple[int, int]:
        while True:
            user_index = np.random.randint(0, self._n_users)
            item_index = np.random.randint(0, self._n_items)
            if (user_index, item_index) not in self._non_zero_indices:
                return user_index, item_index

    def __getitem__(self, indices: Union[int, List[int]]) -> Tuple[Tuple[np.ndarray, np.ndarray], np.ndarray]:
        if isinstance(indices, int):
            indices = [indices]

        n = super().__len__()

        positive_indices = [index for index in indices if index < n]
        num_of_negatives = len(indices) - len(positive_indices)

        positive_batch: Tuple[Tuple[np.ndarray, np.ndarray], np.ndarray] = super().__getitem__(positive_indices)
        if num_of_negatives > 0:
            negative_batch: Tuple[Tuple[List[int], List[int]], np.ndarray] = (tuple(zip(*[
                self._generate_negative_indices()
                for _ in
                range(num_of_negatives)])), np.zeros(num_of_negatives))

            return (np.append(positive_batch[0][0], negative_batch[0][0]),
                    np.append(positive_batch[0][1], negative_batch[0][1])), \
                   np.append(positive_batch[1], negative_batch[1])
        else:
            return (positive_batch[0][0], positive_batch[0][1]), positive_batch[1]


class UserTripletWithOnlineRandomNegativeGenerationDataset(BinaryInteractionsWithOnlineRandomNegativeGenerationDataset):
    def __len__(self) -> int:
        return self._data_frame.shape[0]

    def _generate_negative_item_index(self, user_index: int) -> int:
        while True:
            item_index = np.random.randint(0, self._n_items)
            if (user_index, item_index) not in self._non_zero_indices:
                return item_index

    def __getitem__(self, indices: Union[int, List[int]]) -> Tuple[Tuple[np.ndarray, np.ndarray, np.ndarray],
                                                                   list]:
        if isinstance(indices, int):
            indices = [indices]

        rows: pd.Series = self._data_frame.iloc[indices]
        user_indices = rows[self._input_columns[0]].values
        positive_item_indices = rows[self._input_columns[1]].values
        negative_item_indices = np.array(
            [self._generate_negative_item_index(user_index) for user_index in user_indices], dtype=np.int64)
        return (user_indices, positive_item_indices, negative_item_indices), []
