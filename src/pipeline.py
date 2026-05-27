"""
TransformPipeline — 可组合的转换步骤链

每个 step 是一个 dict，type 字段决定转换类型。
管线可序列化为 JSON 保存/加载。
"""

from __future__ import annotations
import re
from typing import Any, Callable
import pandas as pd


class TransformError(Exception):
    pass


# ── 转换步骤注册表 ────────────────────────────────────────
_TRANSFORMS: dict[str, Callable] = {}


def register_transform(type_name: str):
    """装饰器：注册转换类型"""
    def decorator(fn):
        _TRANSFORMS[type_name] = fn
        return fn
    return decorator


def get_transform(type_name: str) -> Callable:
    if type_name not in _TRANSFORMS:
        raise TransformError(f"未知转换类型: {type_name}")
    return _TRANSFORMS[type_name]


# ── 内置转换步骤 ──────────────────────────────────────────

@register_transform("rename_columns")
def _transform_rename(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """重命名列: {"map": {"old": "new"}}"""
    mapping = config.get("map", {})
    valid = {k: v for k, v in mapping.items() if k in df.columns}
    return df.rename(columns=valid)


@register_transform("select_columns")
def _transform_select(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """选择列: {"columns": ["col1", "col2"]}"""
    cols = config.get("columns", [])
    available = [c for c in cols if c in df.columns]
    return df[available].copy() if available else df


@register_transform("drop_columns")
def _transform_drop(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """删除列: {"columns": ["col1"]}"""
    cols = [c for c in config.get("columns", []) if c in df.columns]
    return df.drop(columns=cols) if cols else df


@register_transform("filter_rows")
def _transform_filter(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    过滤行:
    {"column": "type", "condition": "equals", "value": "ht"}
    {"column": "depth", "condition": "not_null"}
    {"column": "value", "condition": "gt", "value": 100}
    """
    col = config.get("column")
    if not col or col not in df.columns:
        return df
    condition = config.get("condition", "equals")
    val = config.get("value")

    if condition == "equals":
        return df[df[col] == val]
    elif condition == "not_equals":
        return df[df[col] != val]
    elif condition == "not_null":
        return df[df[col].notna()]
    elif condition == "gt":
        return df[pd.to_numeric(df[col], errors="coerce") > float(val)]
    elif condition == "lt":
        return df[pd.to_numeric(df[col], errors="coerce") < float(val)]
    elif condition == "contains":
        return df[df[col].astype(str).str.contains(str(val), na=False)]
    elif condition == "regex":
        return df[df[col].astype(str).str.match(str(val), na=False)]
    return df


@register_transform("sort")
def _transform_sort(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """排序: {"by": "col1", "ascending": true} 或 {"by": ["col1","col2"]}"""
    by = config.get("by")
    ascending = config.get("ascending", True)
    if isinstance(by, str):
        by = [by]
        ascending = [ascending] if isinstance(ascending, bool) else [ascending]
    available = [c for c in by if c in df.columns]
    if not available:
        return df
    return df.sort_values(by=available, ascending=ascending, na_position="last").reset_index(drop=True)


@register_transform("compute_column")
def _transform_compute(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    计算列: {"name": "Kmass", "formula": "Kvol * vol / mass"}
    
    formula 中的变量名对应 df 的列名。
    支持: +, -, *, /, **, sqrt, abs, log, round
    """
    name = config.get("name", "new_col")
    formula = config.get("formula", "")
    if not formula:
        return df

    # 安全的数学环境
    import numpy as np
    safe_env = {
        "sqrt": np.sqrt, "abs": np.abs,
        "log": np.log, "log10": np.log10,
        "round": round, "int": int, "float": float,
        "sin": np.sin, "cos": np.cos, "tan": np.tan,
        "pi": 3.141592653589793,
    }

    # 将列名注入环境
    eval_env = {}
    for col in df.columns:
        # 清理列名使其可作为变量名
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(col))
        eval_env[safe_name] = pd.to_numeric(df[col], errors="coerce")
        if safe_name != col:
            # 也用原始名（如果合法）
            if col.isidentifier():
                eval_env[col] = eval_env[safe_name]

    eval_env.update(safe_env)

    try:
        # 替换公式中的列名
        result = eval(formula, {"__builtins__": {}}, eval_env)
        df[name] = result
    except Exception as e:
        raise TransformError(f"计算列 '{name}' 失败: {e}\n公式: {formula}\n可用变量: {list(eval_env.keys())}")

    return df


@register_transform("add_constant")
def _transform_add_constant(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """添加常量列: {"name": "source", "value": "file1.txt"}"""
    name = config.get("name", "new_col")
    value = config.get("value", "")
    df[name] = value
    return df


@register_transform("clean_column")
def _transform_clean(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """清理列: {"column": "SampleID", "remove_pattern": "DirOKir|Dir"}"""
    col = config.get("column")
    pattern = config.get("remove_pattern", "")
    if not col or col not in df.columns or not pattern:
        return df
    df[col] = df[col].astype(str).str.replace(pattern, "", regex=True).str.strip()
    return df


@register_transform("strip_columns")
def _transform_strip(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """去除列名和值的首尾空格"""
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df


# ── 管线执行器 ────────────────────────────────────────────

def apply_pipeline(df: pd.DataFrame, steps: list[dict]) -> pd.DataFrame:
    """
    按顺序执行转换管线
    
    Args:
        df: 输入 DataFrame
        steps: 转换步骤列表 [{"type": "rename_columns", "map": {...}}, ...]
    
    Returns:
        转换后的 DataFrame
    """
    result = df.copy()
    for i, step in enumerate(steps):
        step_type = step.get("type")
        if not step_type:
            continue
        transform_fn = get_transform(step_type)
        try:
            result = transform_fn(result, step)
        except TransformError:
            raise
        except Exception as e:
            raise TransformError(f"步骤 {i+1} ({step_type}) 执行失败: {e}")
    return result


def pipeline_to_json(steps: list[dict]) -> str:
    """管线序列化为 JSON"""
    import json
    return json.dumps(steps, ensure_ascii=False, indent=2)


def pipeline_from_json(text: str) -> list[dict]:
    """从 JSON 加载管线"""
    import json
    return json.loads(text)
