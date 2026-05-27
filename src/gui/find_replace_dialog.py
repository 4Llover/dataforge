"""
查找替换对话框
迁移自 paleomag-tool
"""

import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialogButtonBox, QComboBox,
)
from PyQt6.QtCore import Qt
import pandas as pd


class FindReplaceDialog(QDialog):
    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.setWindowTitle("查找和替换")
        self.setMinimumSize(600, 500)
        self._df = df.copy()
        self._result_df = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 查找/替换输入
        input_group = QGroupBox("查找和替换")
        input_layout = QVBoxLayout(input_group)

        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("查找:"))
        self.edit_find = QLineEdit()
        self.edit_find.setPlaceholderText("输入要查找的内容...")
        find_row.addWidget(self.edit_find)
        input_layout.addLayout(find_row)

        replace_row = QHBoxLayout()
        replace_row.addWidget(QLabel("替换:"))
        self.edit_replace = QLineEdit()
        self.edit_replace.setPlaceholderText("替换为...（留空则删除）")
        replace_row.addWidget(self.edit_replace)
        input_layout.addLayout(replace_row)

        # 选项
        opt_row = QHBoxLayout()
        self.chk_regex = QCheckBox("正则表达式")
        self.chk_whole = QCheckBox("全字匹配")
        self.chk_case = QCheckBox("区分大小写")
        opt_row.addWidget(self.chk_regex)
        opt_row.addWidget(self.chk_whole)
        opt_row.addWidget(self.chk_case)
        opt_row.addStretch()
        input_layout.addLayout(opt_row)

        # 作用范围
        scope_row = QHBoxLayout()
        scope_row.addWidget(QLabel("作用列:"))
        self.combo_col = QComboBox()
        self.combo_col.addItem("所有列")
        for col in self._df.columns:
            self.combo_col.addItem(col)
        scope_row.addWidget(self.combo_col)
        scope_row.addStretch()
        input_layout.addLayout(scope_row)

        layout.addWidget(input_group)

        # 按钮
        btn_row = QHBoxLayout()
        btn_count = QPushButton("🔍 统计匹配数")
        btn_count.clicked.connect(self._count_matches)
        btn_replace_all = QPushButton("⚡ 全部替换")
        btn_replace_all.setObjectName("btnPrimary")
        btn_replace_all.clicked.connect(self._replace_all)
        btn_row.addWidget(btn_count)
        btn_row.addWidget(btn_replace_all)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 匹配预览
        self.match_table = QTableWidget(0, 4)
        self.match_table.setHorizontalHeaderLabels(["行号", "列名", "原始值", "替换后"])
        self.match_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.match_table, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("应用")
        layout.addWidget(buttons)

    def _get_pattern(self):
        find_text = self.edit_find.text()
        if not find_text:
            return None
        if self.chk_regex.isChecked():
            flags = 0 if self.chk_case.isChecked() else re.IGNORECASE
            return re.compile(find_text, flags)
        else:
            escaped = re.escape(find_text)
            if self.chk_whole.isChecked():
                escaped = r"\b" + escaped + r"\b"
            flags = 0 if self.chk_case.isChecked() else re.IGNORECASE
            return re.compile(escaped, flags)

    def _get_target_columns(self):
        idx = self.combo_col.currentIndex()
        if idx == 0:
            return list(self._df.columns)
        return [self.combo_col.currentText()]

    def _count_matches(self):
        pattern = self._get_pattern()
        if not pattern:
            return
        cols = self._get_target_columns()
        count = 0
        for col in cols:
            for val in self._df[col].astype(str):
                if pattern.search(val):
                    count += 1
        QMessageBox.information(self, "匹配统计", f"共找到 {count} 处匹配")

    def _replace_all(self):
        pattern = self._get_pattern()
        if not pattern:
            return
        replace_text = self.edit_replace.text()
        cols = self._get_target_columns()
        df = self._df.copy()

        self.match_table.setRowCount(0)
        replace_count = 0

        for col in cols:
            for i in range(len(df)):
                old_val = str(df.at[i, col]) if i in df.index else ""
                if pattern.search(old_val):
                    new_val = pattern.sub(replace_text, old_val)
                    if old_val != new_val:
                        df.at[i, col] = new_val
                        row = self.match_table.rowCount()
                        self.match_table.insertRow(row)
                        self.match_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
                        self.match_table.setItem(row, 1, QTableWidgetItem(col))
                        self.match_table.setItem(row, 2, QTableWidgetItem(old_val[:80]))
                        self.match_table.setItem(row, 3, QTableWidgetItem(new_val[:80]))
                        replace_count += 1

        self._result_df = df
        QMessageBox.information(self, "替换完成", f"共替换 {replace_count} 处")

    def _on_accept(self):
        if self._result_df is None:
            self._result_df = self._df
        self.accept()

    def get_result_df(self) -> pd.DataFrame:
        return self._result_df if self._result_df is not None else self._df
