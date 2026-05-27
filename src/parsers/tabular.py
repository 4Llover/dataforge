"""
通用表格文件解析器 — Excel / CSV / TSV
"""

import pandas as pd
from .base import ParserBase


class TabularParser(ParserBase):
    name = "tabular"
    extensions = ["xlsx", "xls", "csv", "txt", "tsv"]
    description = "Excel / CSV / TSV 表格文件"

    def detect(self, filepath: str) -> bool:
        ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
        return ext in self.extensions

    def parse(self, filepath: str, **kwargs) -> pd.DataFrame:
        """
        kwargs:
            sheet_name: Excel sheet 名
            encoding: 编码
            separator: 分隔符
            header_row: 表头行号（0-indexed）
            skip_rows: 要跳过的行号列表
        """
        ext = filepath.rsplit(".", 1)[-1].lower()
        sep = kwargs.get("separator", "\t")
        enc = kwargs.get("encoding")
        header_row = kwargs.get("header_row", 0)
        skip_rows = kwargs.get("skip_rows")

        if ext in ("xlsx", "xls"):
            sheet = kwargs.get("sheet_name", 0)
            return pd.read_excel(filepath, sheet_name=sheet, header=header_row, skiprows=skip_rows)
        elif ext == "csv":
            return self._read_csv(filepath, sep=",", enc=enc, header=header_row, skip_rows=skip_rows)
        else:
            return self._read_csv(filepath, sep=sep, enc=enc, header=header_row, skip_rows=skip_rows)

    def _read_csv(self, filepath, sep=",", enc=None, header=0, skip_rows=None):
        encodings = [enc] if enc else ["utf-8", "gbk", "gb2312", "latin-1"]
        for e in encodings:
            try:
                return pd.read_csv(
                    filepath, sep=sep, encoding=e,
                    header=header, skiprows=skip_rows,
                    on_bad_lines="skip",
                )
            except (UnicodeDecodeError, UnicodeError):
                continue
        return pd.read_csv(filepath, sep=sep, header=header, skiprows=skip_rows, on_bad_lines="skip")
