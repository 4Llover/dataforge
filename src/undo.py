"""
UndoStack — 命令模式撤销/重做

每个操作压栈，Ctrl+Z 撤销，Ctrl+Y 重做。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
import pandas as pd


@dataclass
class UndoEntry:
    """一条撤销记录"""
    description: str
    snapshot: pd.DataFrame  # 操作前的 DataFrame 快照


class UndoStack:
    """撤销/重做栈"""

    def __init__(self, max_size: int = 50):
        self._undo_stack: list[UndoEntry] = []
        self._redo_stack: list[UndoEntry] = []
        self._max_size = max_size

    def push(self, description: str, snapshot: pd.DataFrame):
        """保存操作前的快照"""
        entry = UndoEntry(description=description, snapshot=snapshot.copy())
        self._undo_stack.append(entry)
        if len(self._undo_stack) > self._max_size:
            self._undo_stack.pop(0)
        # 新操作清空 redo 栈
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(self, current_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        """撤销，返回 (恢复的DataFrame, 描述)"""
        if not self._undo_stack:
            return current_df, ""

        entry = self._undo_stack.pop()
        # 把当前状态存入 redo 栈
        self._redo_stack.append(UndoEntry(
            description=entry.description,
            snapshot=current_df.copy(),
        ))
        return entry.snapshot, entry.description

    def redo(self, current_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        """重做，返回 (恢复的DataFrame, 描述)"""
        if not self._redo_stack:
            return current_df, ""

        entry = self._redo_stack.pop()
        # 把当前状态存入 undo 栈
        self._undo_stack.append(UndoEntry(
            description=entry.description,
            snapshot=current_df.copy(),
        ))
        return entry.snapshot, entry.description

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def undo_description(self) -> str:
        if self._undo_stack:
            return self._undo_stack[-1].description
        return ""

    @property
    def redo_description(self) -> str:
        if self._redo_stack:
            return self._redo_stack[-1].description
        return ""
