"""解析器包"""
from .base import ParserBase, ParserRegistry
from .pmd import PmdParser
from .dir import DirParser
from .tabular import TabularParser
from .generic_text import GenericTextParser

# 自动注册
ParserRegistry.register(PmdParser())
ParserRegistry.register(DirParser())
ParserRegistry.register(TabularParser())
ParserRegistry.register(GenericTextParser())
