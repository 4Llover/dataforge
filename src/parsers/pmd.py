"""
PMD 格式解析器 — 逐步热退磁数据

支持从 DetectResult 接收表头列名和数据起始行。
"""

import re
import pandas as pd
from .base import ParserBase


class PmdParser(ParserBase):
    name = "pmd"
    extensions = ["pmd", "dat"]
    description = "逐步热退磁数据 (PMD/DAT)"

    SPECIMEN_PATTERN = re.compile(
        r"^(\S+)\s+a=\s*([\d.]+)\s+b=\s*([\d.]+)\s+s=\s*([\d.]+)\s+d=\s*([\d.]+)\s+v=\s*([\d.Ee+\-]+)"
    )
    HEADER_PATTERN = re.compile(
        r"Xc\s*\(Am2\)|Yc\s*\(Am2\)|Zc\s*\(Am2\)|MAG\s*\(A/m\)|MAG\(A/m\)",
        re.IGNORECASE,
    )
    DATA_PATTERN = re.compile(r"^\d+")

    def detect(self, filepath: str) -> bool:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(2048)
        return bool(self.HEADER_PATTERN.search(content))

    def parse(self, filepath: str, **kwargs) -> pd.DataFrame:
        custom_cols = kwargs.get("header_columns")
        data_start = kwargs.get("data_start_row")

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

        rows = []
        current_specimen = ""

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line == "\x1a":
                continue

            spec_match = self.SPECIMEN_PATTERN.match(line)
            if spec_match:
                current_specimen = spec_match.group(1)
                continue

            if self.HEADER_PATTERN.search(line):
                continue

            if self.DATA_PATTERN.match(line):
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        rows.append({
                            "specimen": current_specimen,
                            "treatment": int(parts[0]),
                            "treatment_type": "T",
                            "xc": float(parts[1]),
                            "yc": float(parts[2]),
                            "zc": float(parts[3]),
                            "MAG": float(parts[4]),
                            "Dg": float(parts[5]),
                            "Ig": float(parts[6]),
                            "Ds": float(parts[7]),
                            "Is": float(parts[8]),
                            "a95": float(parts[9]),
                        })
                    except (ValueError, IndexError):
                        continue

        if not rows:
            raise ValueError(f"未能从文件中解析出任何数据行: {filepath}")

        df = pd.DataFrame(rows)
        column_order = [
            "specimen", "treatment", "treatment_type",
            "xc", "yc", "zc", "MAG",
            "Dg", "Ig", "Ds", "Is", "a95"
        ]
        return df[[c for c in column_order if c in df.columns]]
