"""
解析器框架 — 可插拔解析器基类 + 注册表

扩展自 paleomag-tool，增加 DetectResult 适配。
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class ParserBase(ABC):
    """解析器抽象基类"""

    name: str = "base"
    extensions: list[str] = []
    description: str = ""

    @abstractmethod
    def parse(self, filepath: str, **kwargs) -> pd.DataFrame:
        """解析文件并返回 DataFrame"""
        ...

    @abstractmethod
    def detect(self, filepath: str) -> bool:
        """检测文件是否可由此解析器处理"""
        ...

    def preview(self, filepath: str, lines: int = 20) -> str:
        """读取文件前 N 行作为预览"""
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return "".join(f.readline() for _ in range(lines))


class ParserRegistry:
    """解析器注册表"""

    _parsers: dict[str, ParserBase] = {}

    @classmethod
    def register(cls, parser: ParserBase) -> None:
        cls._parsers[parser.name] = parser

    @classmethod
    def get_by_extension(cls, ext: str) -> Optional[ParserBase]:
        ext = ext.lower().lstrip(".")
        for parser in cls._parsers.values():
            if ext in parser.extensions:
                return parser
        return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional[ParserBase]:
        return cls._parsers.get(name)

    @classmethod
    def list_all(cls) -> list[ParserBase]:
        return list(cls._parsers.values())

    @classmethod
    def supported_extensions(cls) -> list[str]:
        exts = []
        for p in cls._parsers.values():
            exts.extend(p.extensions)
        return sorted(set(exts))

    @classmethod
    def parse_file(cls, filepath: str, parser_name: str = None, **kwargs) -> pd.DataFrame:
        """解析文件，可指定解析器名或自动检测"""
        if parser_name:
            parser = cls.get_by_name(parser_name)
            if parser:
                return parser.parse(filepath, **kwargs)

        # 按扩展名尝试
        ext = filepath.rsplit(".", 1)[-1] if "." in filepath else ""
        parser = cls.get_by_extension(ext)
        if parser:
            return parser.parse(filepath, **kwargs)

        # 兜底通用文本
        fallback = cls.get_by_name("generic_text")
        if fallback:
            return fallback.parse(filepath, **kwargs)

        raise ValueError(f"无法解析文件: {filepath}")
