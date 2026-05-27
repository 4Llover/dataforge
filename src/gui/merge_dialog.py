"""
合并向导对话框

支持：
  1. 纵向追加 (concat) — 多文件行堆叠
  2. 横向匹配合并 (join) — 按键列合并
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QRadioButton, QButtonGroup,
    QDialogButtonBox, QCheckBox, QListWidget, QListWidgetItem,
    QAbstractItemView, QMessageBox, QSplitter, QTableView,
    QHeaderView, QDoubleSpinBox,
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
import pandas as pd

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from merger import MergeConfig, MergeMode, merge_tables


class MergeDialog(QDialog):
    """合并向导"""

    def __init__(self, loaded_files: dict[str, pd.DataFrame], parent=None):
        super().__init__(parent)
        self.setWindowTitle("合并向导")
        self.setMinimumSize(800, 600)
        self._loaded_files = loaded_files  # {filepath: DataFrame}
        self._result_df = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── 文件选择 ──
        file_group = QGroupBox("选择要合并的文件")
        fl = QVBoxLayout(file_group)
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for path, df in self._loaded_files.items():
            name = path.split("/")[-1].split("\\")[-1]
            item = QListWidgetItem(f"{name}  ({len(df)} 行, {len(df.columns)} 列)")
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.file_list.addItem(item)
        # 默认全选
        self.file_list.selectAll()
        fl.addWidget(self.file_list)
        layout.addWidget(file_group)

        # ── 合并模式 ──
        mode_group = QGroupBox("合并模式")
        ml = QVBoxLayout(mode_group)

        self._mode_group = QButtonGroup(self)
        self.rb_concat = QRadioButton("纵向追加 (concat) — 列名对齐，行堆叠")
        self.rb_concat.setToolTip("适合: 多个同格式文件合并成一张大表")
        self.rb_concat.setChecked(True)
        self.rb_join = QRadioButton("横向匹配合并 (join) — 按键列匹配合并")
        self.rb_join.setToolTip("适合: 两个不同格式文件按样品名匹配合并")
        self._mode_group.addButton(self.rb_concat, 0)
        self._mode_group.addButton(self.rb_join, 1)
        ml.addWidget(self.rb_concat)
        ml.addWidget(self.rb_join)

        # concat 选项
        self._concat_widget = QCheckBox("添加「_来源」列标记数据来源")
        self._concat_widget.setChecked(True)
        ml.addWidget(self._concat_widget)

        # join 选项
        self._join_widget = QGroupBox("匹配套配置")
        jl = QVBoxLayout(self._join_widget)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("左表键列:"))
        self.combo_left_key = QComboBox()
        key_row.addWidget(self.combo_left_key)
        key_row.addWidget(QLabel("右表键列:"))
        self.combo_right_key = QComboBox()
        key_row.addWidget(self.combo_right_key)
        jl.addLayout(key_row)

        how_row = QHBoxLayout()
        how_row.addWidget(QLabel("合并方式:"))
        self.combo_how = QComboBox()
        self.combo_how.addItems(["left (保留左表全部)", "inner (仅匹配行)", "outer (保留全部)", "right (保留右表全部)"])
        self.combo_how.setCurrentIndex(0)
        how_row.addWidget(self.combo_how)
        how_row.addStretch()
        jl.addLayout(how_row)

        ml.addWidget(self._join_widget)
        self._join_widget.setVisible(False)

        self.rb_concat.toggled.connect(lambda c: self._concat_widget.setVisible(c))
        self.rb_concat.toggled.connect(lambda c: self._join_widget.setVisible(not c))
        self.rb_join.toggled.connect(self._update_join_columns)

        layout.addWidget(mode_group)

        # ── 预览按钮 ──
        btn_row = QHBoxLayout()
        btn_preview = QPushButton("🔍 预览合并结果")
        btn_preview.setObjectName("btnPrimary")
        btn_preview.clicked.connect(self._do_preview)
        btn_row.addWidget(btn_preview)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── 结果预览 ──
        self.lbl_result = QLabel("尚未执行合并")
        self.lbl_result.setStyleSheet("color:#86868B; font-size:12px;")
        layout.addWidget(self.lbl_result)

        # ── 按钮 ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("确认合并")
        ok_btn.setEnabled(False)
        self._ok_btn = ok_btn
        layout.addWidget(buttons)

    def _get_selected_files(self) -> list[tuple[str, pd.DataFrame]]:
        result = []
        for item in self.file_list.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self._loaded_files:
                name = path.split("/")[-1].split("\\")[-1]
                result.append((name, self._loaded_files[path]))
        return result

    def _update_join_columns(self):
        files = self._get_selected_files()
        self.combo_left_key.clear()
        self.combo_right_key.clear()
        if len(files) >= 1:
            self.combo_left_key.addItems(list(files[0][1].columns))
        if len(files) >= 2:
            self.combo_right_key.addItems(list(files[1][1].columns))
            # 智能推荐同名键列
            left_cols = set(files[0][1].columns)
            right_cols = set(files[1][1].columns)
            common = left_cols & right_cols
            if common:
                first_common = sorted(common)[0]
                self.combo_left_key.setCurrentText(first_common)
                self.combo_right_key.setCurrentText(first_common)

    def _do_preview(self):
        files = self._get_selected_files()
        if len(files) < 2:
            QMessageBox.warning(self, "文件不足", "请至少选择 2 个文件")
            return

        tables = [df for _, df in files]
        names = [name for name, _ in files]

        if self.rb_concat.isChecked():
            config = MergeConfig(
                mode=MergeMode.CONCAT,
                add_source_col=self._concat_widget.isChecked(),
            )
        else:
            how_idx = self.combo_how.currentIndex()
            how_map = {0: "left", 1: "inner", 2: "outer", 3: "right"}
            config = MergeConfig(
                mode=MergeMode.JOIN,
                join_key_left=self.combo_left_key.currentText(),
                join_key_right=self.combo_right_key.currentText(),
                join_how=how_map.get(how_idx, "left"),
            )

        result = merge_tables(tables, config, names)
        self._result_df = result.df
        self.lbl_result.setText(result.summary)
        self.lbl_result.setStyleSheet("color:#34C759; font-size:12px; font-weight:600;")
        self._ok_btn.setEnabled(True)

    def _on_accept(self):
        if self._result_df is None:
            self._do_preview()
        if self._result_df is not None:
            self.accept()
        else:
            QMessageBox.warning(self, "未合并", "请先预览合并结果")

    def get_result_df(self) -> pd.DataFrame:
        return self._result_df
