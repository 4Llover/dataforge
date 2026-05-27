"""
DIR 格式解析器 — 方向数据
"""

import re
import pandas as pd
from .base import ParserBase


class DirParser(ParserBase):
    name = "dir"
    extensions = ["dir"]
    description = "方向数据 (DIR)"

    SAMPLE_CLEAN_PATTERN = re.compile(r"DirOKir|Dir\s*Kir|Dir", re.IGNORECASE)

    def detect(self, filepath: str) -> bool:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 9 and parts[-1].lower() in ("ht", "lt"):
                    return True
        return False

    def parse(self, filepath: str, **kwargs) -> pd.DataFrame:
        """
        kwargs:
            ht_only: bool — 只保留 ht 行（默认 True）
            encoding: str — 编码
        """
        ht_only = kwargs.get("ht_only", True)
        rows = []

        # 多编码尝试
        lines = None
        for enc in [kwargs.get("encoding", "utf-8"), "utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                with open(filepath, "r", encoding=enc, errors="strict") as f:
                    lines = f.readlines()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if lines is None:
            with open(filepath, "r", encoding="latin-1", errors="replace") as f:
                lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or line == "\x1a":
                continue
            parts = line.split()
            if len(parts) < 9:
                continue

            row_type = parts[-1].lower()
            if ht_only and row_type != "ht":
                continue

            sample_raw = parts[0]
            sample_clean = self.SAMPLE_CLEAN_PATTERN.sub("", sample_raw).strip()

            try:
                rows.append({
                    "SampleID": sample_clean,
                    "treatment": parts[1],
                    "N": int(parts[2]),
                    "Dg": float(parts[3]),
                    "Ig": float(parts[4]),
                    "Ds": float(parts[5]),
                    "Is": float(parts[6]),
                    "a95": float(parts[7]),
                    "type": row_type.upper(),
                })
            except (ValueError, IndexError):
                continue

        if not rows:
            raise ValueError(f"未能从文件中解析出任何数据行: {filepath}")

        df = pd.DataFrame(rows)
        column_order = ["SampleID", "treatment", "N", "Dg", "Ig", "Ds", "Is", "a95", "type"]
        return df[[c for c in column_order if c in df.columns]]
