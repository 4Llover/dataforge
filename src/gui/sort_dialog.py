"""
排序对话框 — 支持单列/多列排序
迁移自 paleomag-tool
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialogButtonBox, QCheckBox, QGroupBox, QAbstractItemView,
    QMessageBox,
)
from PyQt6.QtCore import Qt
import pandas as pd


class SortDialog(QDialog):
    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.setWindowTitle("排序")
        self.setMinimumSize(500, 450)
        self._df = df.copy()
        self._sorted_df = None
        self._columns = list(df.columns)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        tip = QLabel("添加排序规则，按优先级从上到下执行。整行数据一起移动。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#86868B; font-size:12px;")
        layout.addWidget(tip)

        self.rule_table = QTableWidget(0, 2)
        self.rule_table.setHorizontalHeaderLabels(["列名", "排序方式"])
        self.rule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rule_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.rule_table)

        rule_btn_row = QHBoxLayout()
        btn_add = QPushButton("➕ 添加规则")
        btn_add.clicked.connect(self._add_rule)
        btn_remove = QPushButton("🗑 删除")
        btn_remove.clicked.connect(self._remove_rule)
        btn_move_up = QPushButton("⬆")
        btn_move_up.clicked.connect(self._move_up)
        btn_move_down = QPushButton("⬇")
        btn_move_down.clicked.connect(self._move_down)
        rule_btn_row.addWidget(btn_add)
        rule_btn_row.addWidget(btn_remove)
        rule_btn_row.addWidget(btn_move_up)
        rule_btn_row.addWidget(btn_move_down)
        layout.addLayout(rule_btn_row)

        opt_group = QGroupBox("选项")
        opt_layout = QVBoxLayout(opt_group)
        self.chk_reset = QCheckBox("重置行号")
        self.chk_reset.setChecked(True)
        opt_layout.addWidget(self.chk_reset)
        self.chk_ignore_case = QCheckBox("忽略大小写")
        self.chk_ignore_case.setChecked(True)
        opt_layout.addWidget(self.chk_ignore_case)
        layout.addWidget(opt_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._add_rule()

    def _add_rule(self):
        row = self.rule_table.rowCount()
        self.rule_table.insertRow(row)
        col_combo = QComboBox()
        col_combo.addItems(self._columns)
        self.rule_table.setCellWidget(row, 0, col_combo)
        order_combo = QComboBox()
        order_combo.addItems(["升序", "降序"])
        self.rule_table.setCellWidget(row, 1, order_combo)

    def _remove_rule(self):
        row = self.rule_table.currentRow()
        if row >= 0:
            self.rule_table.removeRow(row)

    def _move_up(self):
        row = self.rule_table.currentRow()
        if row > 0:
            for col in range(self.rule_table.columnCount()):
                w1 = self.rule_table.cellWidget(row, col)
                w2 = self.rule_table.cellWidget(row - 1, col)
                if isinstance(w1, QComboBox) and isinstance(w2, QComboBox):
                    i1, i2 = w1.currentIndex(), w2.currentIndex()
                    w1.setCurrentIndex(i2)
                    w2.setCurrentIndex(i1)
            self.rule_table.setCurrentCell(row - 1, 0)

    def _move_down(self):
        row = self.rule_table.currentRow()
        if row < self.rule_table.rowCount() - 1:
            for col in range(self.rule_table.columnCount()):
                w1 = self.rule_table.cellWidget(row, col)
                w2 = self.rule_table.cellWidget(row + 1, col)
                if isinstance(w1, QComboBox) and isinstance(w2, QComboBox):
                    i1, i2 = w1.currentIndex(), w2.currentIndex()
                    w1.setCurrentIndex(i2)
                    w2.setCurrentIndex(i1)
            self.rule_table.setCurrentCell(row + 1, 0)

    def _on_accept(self):
        if self.rule_table.rowCount() == 0:
            self._sorted_df = self._df
            self.accept()
            return

        sort_cols = []
        sort_ascending = []
        for row in range(self.rule_table.rowCount()):
            col_combo = self.rule_table.cellWidget(row, 0)
            order_combo = self.rule_table.cellWidget(row, 1)
            if col_combo and order_combo:
                sort_cols.append(col_combo.currentText())
                sort_ascending.append(order_combo.currentIndex() == 0)

        if not sort_cols:
            self._sorted_df = self._df
            self.accept()
            return

        df = self._df.copy()
        if self.chk_ignore_case.isChecked():
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str).str.lower()

        try:
            self._sorted_df = df.sort_values(
                by=sort_cols, ascending=sort_ascending,
                na_position="last", kind="mergesort",
                ignore_index=self.chk_reset.isChecked(),
            )
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "排序失败", str(e))

    def get_sorted_df(self) -> pd.DataFrame:
        return self._sorted_df if self._sorted_df is not None else self._df
