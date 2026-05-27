"""
数据匹配引擎 — 跨表数据匹配与回填
迁移自 paleomag-tool
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
from difflib import SequenceMatcher


class MatchMode(Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"


@dataclass
class MatchConfig:
    target_key: str
    source_key: str
    fill_columns: list[str] = field(default_factory=list)
    mode: MatchMode = MatchMode.EXACT
    fuzzy_threshold: float = 0.75


@dataclass
class MatchResult:
    matched_df: pd.DataFrame
    match_count: int
    total_target: int
    unmatched_keys: list[str]
    summary: str


def _normalize_text(val) -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip().lower()
    s = re.sub(r'\s+', ' ', s)
    return s


def _similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def match_and_fill(
    target_df: pd.DataFrame,
    source_df: pd.DataFrame,
    config: MatchConfig,
) -> MatchResult:
    target = target_df.copy()
    source = source_df.copy()
    total_target = len(target)

    if config.target_key not in target.columns:
        raise ValueError(f"目标表不存在列「{config.target_key}」")
    if config.source_key not in source.columns:
        raise ValueError(f"源表不存在列「{config.source_key}」")

    fill_cols = [c for c in config.fill_columns if c in source.columns]
    if not fill_cols:
        raise ValueError("没有可回填的列")

    source_dedup = source.drop_duplicates(subset=[config.source_key], keep="first")
    unmatched_keys = []

    if config.mode == MatchMode.EXACT:
        source_dedup = source_dedup.copy()
        source_dedup["_norm_key"] = source_dedup[config.source_key].apply(_normalize_text)
        source_index = source_dedup.set_index("_norm_key")

        matched_count = 0
        for i, t_val in target[config.target_key].items():
            t_key = _normalize_text(t_val)
            if t_key and t_key in source_index.index:
                for col in fill_cols:
                    target.at[i, col] = source_index.at[t_key, col]
                matched_count += 1
            else:
                unmatched_keys.append(str(t_val))

    elif config.mode == MatchMode.FUZZY:
        source_norm_index = {}
        for idx, val in source_dedup[config.source_key].items():
            norm = _normalize_text(val)
            source_norm_index[norm] = idx

        matched_count = 0
        for i, t_val in target[config.target_key].items():
            t_norm = _normalize_text(t_val)
            if not t_norm:
                unmatched_keys.append(str(t_val))
                continue

            if t_norm in source_norm_index:
                s_idx = source_norm_index[t_norm]
                for col in fill_cols:
                    target.at[i, col] = source_dedup.at[s_idx, col]
                matched_count += 1
                continue

            best_score = 0.0
            best_norm = None
            for s_norm in source_norm_index:
                score = _similarity(t_norm, s_norm)
                if score > best_score:
                    best_score = score
                    best_norm = s_norm

            if best_norm and best_score >= config.fuzzy_threshold:
                s_idx = source_norm_index[best_norm]
                for col in fill_cols:
                    target.at[i, col] = source_dedup.at[s_idx, col]
                matched_count += 1
            else:
                unmatched_keys.append(str(t_val))

    pct = (matched_count / total_target * 100) if total_target > 0 else 0
    summary = f"匹配成功: {matched_count}/{total_target} 行 ({pct:.1f}%)"

    return MatchResult(
        matched_df=target,
        match_count=matched_count,
        total_target=total_target,
        unmatched_keys=unmatched_keys,
        summary=summary,
    )
