"""
列操作面板 — 列选择 + 重命名 + 计算列

右侧嵌入主窗口。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPushButton, QScrollArea, QGroupBox, QLineEdit, QInputDialog,
    QMessageBox, QComboBox, QDialog, QDialogButtonBox, QTextEdit,
    QFormLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

import pandas as pd


class ColumnPanel(QWidget):
    """列操作面板"""

    # 信号：列选择变化 → 主窗口刷新表格
    columns_changed = pyqtSignal(list)  # 选中的列名列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkboxes: dict[str, QCheckBox] = {}
        self._renames: dict[str, str] = {}  # 原名 → 新名
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        lbl = QLabel("📋 列操作")
        lbl.setStyleSheet("font-size:15px; font-weight:700; color:#1D1D1F;")
        layout.addWidget(lbl)

        # 全选/清空/反选
        sel_row = QHBoxLayout()
        btn_all = QPushButton("全选")
        btn_all.clicked.connect(lambda: self._toggle_all(True))
        btn_none = QPushButton("清空")
        btn_none.clicked.connect(lambda: self._toggle_all(False))
        btn_invert = QPushButton("反选")
        btn_invert.clicked.connect(self._invert)
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        sel_row.addWidget(btn_invert)
        layout.addLayout(sel_row)

        # 列复选框滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._container = QWidget()
        self._checkbox_layout = QVBoxLayout(self._container)
        self._checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self._checkbox_layout.setSpacing(2)
        scroll.setWidget(self._container)
        layout.addWidget(scroll, stretch=1)

        # 底部按钮
        btn_row = QHBoxLayout()

        btn_apply = QPushButton("✅ 应用列选择")
        btn_apply.setObjectName("btnPrimary")
        btn_apply.clicked.connect(self._emit_selection)
        btn_row.addWidget(btn_apply)

        btn_rename = QPushButton("✏️ 批量改名")
        btn_rename.clicked.connect(self._batch_rename)
        btn_row.addWidget(btn_rename)

        layout.addLayout(btn_row)

        # 计算列
        calc_group = QGroupBox("➕ 添加计算列")
        calc_layout = QVBoxLayout(calc_group)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("列名:"))
        self.edit_col_name = QLineEdit()
        self.edit_col_name.setPlaceholderText("如: Kmass")
        name_row.addWidget(self.edit_col_name)
        calc_layout.addLayout(name_row)

        formula_row = QHBoxLayout()
        formula_row.addWidget(QLabel("公式:"))
        self.edit_formula = QLineEdit()
        self.edit_formula.setPlaceholderText("如: Kvol * volume / mass  (用列名作变量)")
        formula_row.addWidget(self.edit_formula)
        calc_layout.addLayout(formula_row)

        btn_calc = QPushButton("⚡ 添加计算列")
        btn_calc.clicked.connect(self._request_compute)
        calc_layout.addWidget(btn_calc)

        layout.addWidget(calc_group)

    def set_columns(self, columns: list[str]):
        """设置列列表（导入新数据时调用）"""
        self._clear()
        self._renames.clear()
        for col in columns:
            cb = QCheckBox(col)
            cb.setChecked(True)
            cb.setToolTip(f"列名: {col}")
            self._checkbox_layout.addWidget(cb)
            self._checkboxes[col] = cb

    def _clear(self):
        while self._checkbox_layout.count():
            item = self._checkbox_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._checkboxes.clear()

    def _toggle_all(self, checked: bool):
        for cb in self._checkboxes.values():
            cb.setChecked(checked)

    def _invert(self):
        for cb in self._checkboxes.values():
            cb.setChecked(not cb.isChecked())

    def get_selected_columns(self) -> list[str]:
        return [col for col, cb in self._checkboxes.items() if cb.isChecked()]

    def get_renames(self) -> dict[str, str]:
        return dict(self._renames)

    def _emit_selection(self):
        self.columns_changed.emit(self.get_selected_columns())

    def _batch_rename(self):
        """批量重命名列"""
        old_names = list(self._checkboxes.keys())
        if not old_names:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("批量重命名列")
        dlg.resize(500, 400)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("每行一个新列名，按顺序对应。不改的保持原名。"))

        edit = QTextEdit()
        current_names = []
        for name in old_names:
            new_name = self._renames.get(name, name)
            current_names.append(new_name)
        edit.setPlainText("\n".join(current_names))
        edit.setFont(QFont("Consolas", 11))
        layout.addWidget(edit)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        layout.addWidget(btn_box)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_names = [n.strip() for n in edit.toPlainText().strip().split("\n") if n.strip()]
        if len(new_names) != len(old_names):
            QMessageBox.warning(self, "列数不匹配", f"原 {len(old_names)} 列，输入 {len(new_names)} 行")
            return

        # 更新重命名映射
        self._renames.clear()
        for old, new in zip(old_names, new_names):
            if old != new:
                self._renames[old] = new

        # 更新复选框文本
        for old, cb in self._checkboxes.items():
            new = self._renames.get(old, old)
            cb.setText(new if new == old else f"{old} → {new}")

        QMessageBox.information(self, "完成", f"已设置 {len(self._renames)} 个列重命名")

    def _request_compute(self):
        """请求添加计算列（发射信号给主窗口处理）"""
        name = self.edit_col_name.text().strip()
        formula = self.edit_formula.text().strip()
        if not name or not formula:
            QMessageBox.warning(self, "输入不完整", "请填写列名和公式")
            return
        self._compute_requested.emit(name, formula)

    # 信号：计算列请求
    compute_requested = pyqtSignal(str, str)  # (col_name, formula)
