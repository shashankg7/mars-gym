import functools
from collections import defaultdict
from typing import Dict, Any, List, Iterable

import numpy as np
import pandas as pd

from mars_gym.meta_config import ProjectConfig, IOType


def create_index_mapping(
    indexable_values: Iterable, include_unkown: bool = True, include_none: bool = True
) -> Dict[Any, int]:
    indexable_values = list(sorted(set(indexable_values)))
    if include_none:
        indexable_values = [None] + indexable_values
    if include_unkown:
        indices = np.arange(1, len(indexable_values) + 1)
        return defaultdict(int, zip(indexable_values, indices))  # Unkown = 0
    else:
        indices = np.arange(0, len(indexable_values))
        return dict(zip(indexable_values, indices))


def create_index_mapping_from_arrays(
    indexable_arrays: Iterable[list],
    include_unkown: bool = True,
    include_none: bool = True,
) -> Dict[Any, int]:
    all_values = set(value for values in indexable_arrays for value in values)
    return create_index_mapping(all_values, include_unkown, include_none)


def _map_array(values: list, mapping: dict) -> List[int]:
    return [mapping[value] for value in values]


def transform_with_indexing(
    df: pd.DataFrame,
    index_mapping: Dict[str, dict],
    project_config: ProjectConfig,
):
    for key, mapping in index_mapping.items():
        column = project_config.get_column_by_name(key)
        if column and key in df:
            if column.type == IOType.INDEXABLE:
                df[key] = df[key].map(mapping)
            elif column.type == IOType.INDEXABLE_ARRAY:
                df[key] = df[key].map(functools.partial(_map_array, mapping=mapping))
    if project_config.available_arms_column_name in df and project_config.item_column.name in index_mapping:
        df[project_config.available_arms_column_name] = df[project_config.available_arms_column_name].map(
            functools.partial(
                _map_array, mapping=index_mapping[project_config.item_column.name]
            )
        )
