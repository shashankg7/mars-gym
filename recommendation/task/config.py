from recommendation.data import InteractionsDataset
from recommendation.task.data_preparation import ifood
from recommendation.task.meta_config import *

PROJECTS: Dict[str, ProjectConfig] = {
    "ifood_contextual_bandit": ProjectConfig(
        base_dir=ifood.BASE_DIR,
        prepare_data_frames_task=ifood.PrepareIfoodSessionsDataFrames,
        dataset_class=InteractionsDataset,
        user_column=Column("account_idx", IOType.INDEX),
        item_column=Column("merchant_idx", IOType.INDEX),
        other_input_columns=[
            Column("shift_idx", IOType.INDEX), Column("hist_visits", IOType.NUMBER), Column("hist_buys", IOType.NUMBER),
        ],
        metadata_columns=[
            Column("trading_name", IOType.INT_ARRAY), Column("description", IOType.INT_ARRAY),
            Column("category_names", IOType.INT_ARRAY), Column("restaurant_complete_info", IOType.FLOAT_ARRAY),
        ],
        output_column=Column("buy", IOType.NUMBER),
        hist_view_column_name="hist_visits",
        hist_output_column_name="hist_buys",
        auxiliar_output_columns=[Column("ps", IOType.NUMBER)],
        recommender_type=RecommenderType.USER_BASED_COLLABORATIVE_FILTERING,
    ),
}
