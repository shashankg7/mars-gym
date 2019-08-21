from enum import Enum, auto
from typing import List, Type

from torch.utils.data import Dataset

from recommendation.task.data_preparation.base import BasePrepareDataFrames

class IOType(Enum):
    INDEX  = auto()
    NUMBER = auto()
    ARRAY  = auto()


class RecommenderType(Enum):
    USER_BASED_COLLABORATIVE_FILTERING = auto()
    ITEM_BASED_COLLABORATIVE_FILTERING = auto()
    CONTENT_BASED = auto()

class Column(object):
    def __init__(self, name: str, type: IOType) -> None:
        self.name = name
        self.type = type


class ProjectConfig(object):
    def __init__(self, base_dir: str,
                 prepare_data_frames_task: Type[BasePrepareDataFrames],
                 dataset_class: Type[Dataset],
                 input_columns: List[Column],
                 output_column: Column,
                 recommender_type: RecommenderType,
                 n_users_column: str = "n_users",
                 n_items_column: str = "n_items",
                 default_balance_fields: List[str] = [],
                 ) -> None:
        self.base_dir = base_dir
        self.prepare_data_frames_task = prepare_data_frames_task
        self.dataset_class = dataset_class
        self.input_columns = input_columns
        self.output_column = output_column
        self.recommender_type = recommender_type
        self.n_users_column = n_users_column
        self.n_items_column = n_items_column
        self.default_balance_fields = default_balance_fields
