"""
MergeEngine — 多表合并引擎

支持：
  1. 纵向合并 (concat) — 列名对齐，行追加
  2. 横向合并 (join) — 按键列匹配合并
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import pandas as pd


class MergeMode(Enum):
    CONCAT = "concat"   # 纵向追加
    JOIN = "join"       # 横向匹配合并


@dataclass
class MergeConfig:
    mode: MergeMode = MergeMode.CONCAT
    join_key_left: str = ""     # join 模式的左表键列
    join_key_right: str = ""    # join 模式的右表键列
    join_how: str = "left"      # left / right / outer / inner
    add_source_col: bool = True  # concat 模式下是否添加来源列


@dataclass
class MergeResult:
    df: pd.DataFrame
    summary: str


def merge_tables(
    tables: list[pd.DataFrame],
    config: MergeConfig,
    names: list[str] = None,
) -> MergeResult:
    """
    合并多个表
    
    Args:
        tables: DataFrame 列表
        config: 合并配置
        names: 表名列表（用于来源标记）
    """
    if not tables:
        return MergeResult(pd.DataFrame(), "无数据可合并")

    if names is None:
        names = [f"表{i+1}" for i in range(len(tables))]

    if config.mode == MergeMode.CONCAT:
        return _merge_concat(tables, config, names)
    elif config.mode == MergeMode.JOIN:
        if len(tables) < 2:
            return MergeResult(tables[0].copy() if tables else pd.DataFrame(), "仅一张表，无需合并")
        return _merge_join(tables[0], tables[1], config, names[0], names[1])

    return MergeResult(pd.DataFrame(), "未知合并模式")


def _merge_concat(
    tables: list[pd.DataFrame],
    config: MergeConfig,
    names: list[str],
) -> MergeResult:
    """纵向合并"""
    frames = []
    for i, df in enumerate(tables):
        df_copy = df.copy()
        if config.add_source_col and len(tables) > 1:
            df_copy["_来源"] = names[i] if i < len(names) else f"表{i+1}"
        frames.append(df_copy)

    merged = pd.concat(frames, ignore_index=True)
    total = sum(len(t) for t in tables)
    summary = f"纵向合并 {len(tables)} 张表 → {len(merged)} 行 (原始共 {total} 行)"
    return MergeResult(merged, summary)


def _merge_join(
    left: pd.DataFrame,
    right: pd.DataFrame,
    config: MergeConfig,
    left_name: str,
    right_name: str,
) -> MergeResult:
    """横向匹配合并"""
    left_key = config.join_key_left
    right_key = config.join_key_right

    if not left_key or not right_key:
        return MergeResult(pd.DataFrame(), "未指定匹配套键列")

    if left_key not in left.columns:
        return MergeResult(pd.DataFrame(), f"左表不存在列「{left_key}」")
    if right_key not in right.columns:
        return MergeResult(pd.DataFrame(), f"右表不存在列「{right_key}」")

    # 避免列名冲突：给右表列加后缀
    right_renamed = right.copy()
    overlap = set(left.columns) & set(right_renamed.columns) - {right_key}
    if overlap:
        rename_map = {col: f"{col}_右" for col in overlap}
        right_renamed = right_renamed.rename(columns=rename_map)

    merged = pd.merge(
        left, right_renamed,
        left_on=left_key, right_on=right_key,
        how=config.join_how,
        suffixes=("", "_右"),
    )

    match_count = merged[left_key].notna().sum()
    summary = (
        f"横向合并: {left_key} ← {right_key} ({config.join_how})\n"
        f"左表 {len(left)} 行 + 右表 {len(right)} 行 → {len(merged)} 行\n"
        f"匹配: {match_count} 行"
    )
    return MergeResult(merged, summary)
