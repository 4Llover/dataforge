"""
通用文本解析器 — 任意分隔符文本文件

依赖 SmartDetector 的识别结果来确定分隔符、表头行、数据起始行。
"""

import re
import pandas as pd
from .base import ParserBase


class GenericTextParser(ParserBase):
    name = "generic_text"
    extensions = []  # 不按扩展名匹配，由 detector 推荐
    description = "通用文本数据（智能解析）"

    def detect(self, filepath: str) -> bool:
        return True  # 兜底，总是返回 True

    def parse(self, filepath: str, **kwargs) -> pd.DataFrame:
        """
        kwargs:
            encoding: str
            separator: str — 分隔符
            header_row: int — 表头行号（-1=无表头）
            data_start_row: int — 数据起始行
            header_columns: list[str] — 自定义列名
        """
        requested_enc = kwargs.get("encoding", "utf-8")
        sep = kwargs.get("separator", "\t")
        header_row = kwargs.get("header_row", -1)
        data_start = kwargs.get("data_start_row", 0)
        custom_cols = kwargs.get("header_columns", [])

        # 多编码尝试读取
        all_lines = None
        encoding_used = requested_enc
        for enc in [requested_enc, "utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                with open(filepath, "r", encoding=enc, errors="strict") as f:
                    all_lines = f.readlines()
                encoding_used = enc
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if all_lines is None:
            with open(filepath, "r", encoding="latin-1", errors="replace") as f:
                all_lines = f.readlines()
            encoding_used = "latin-1"

        # 确定跳过哪些行
        skip_rows = []
        for i in range(data_start):
            if i != header_row:
                skip_rows.append(i)

        # 提取数据行
        data_lines = all_lines[data_start:]
        if not data_lines:
            raise ValueError(f"文件无数据行: {filepath}")

        # 解析数据
        rows = []
        for line in data_lines:
            stripped = line.strip()
            if not stripped or stripped == "\x1a":
                continue
            parts = stripped.split(sep) if sep else stripped.split()
            parts = [p.strip() for p in parts if p.strip()]
            if parts:
                rows.append(parts)

        if not rows:
            raise ValueError(f"未能解析出数据: {filepath}")

        # 确定列数（取众数）
        from collections import Counter
        col_counts = Counter(len(r) for r in rows)
        expected_cols = col_counts.most_common(1)[0][0]

        # 过滤掉列数不对的行
        rows = [r for r in rows if len(r) == expected_cols]

        if not rows:
            raise ValueError(f"数据行列数不一致: {filepath}")

        # 确定列名
        if custom_cols and len(custom_cols) == expected_cols:
            columns = custom_cols
        elif header_row >= 0 and header_row < len(all_lines):
            header_line = all_lines[header_row].strip()
            header_parts = header_line.split(sep) if sep else header_line.split()
            header_parts = [p.strip() for p in header_parts if p.strip()]
            if len(header_parts) == expected_cols:
                columns = header_parts
            else:
                columns = [f"col_{i+1}" for i in range(expected_cols)]
        else:
            columns = [f"col_{i+1}" for i in range(expected_cols)]

        # 构建 DataFrame
        df = pd.DataFrame(rows, columns=columns)

        # 尝试数值转换
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass

        return df
