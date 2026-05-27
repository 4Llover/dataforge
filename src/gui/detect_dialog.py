"""
格式识别预览对话框

拖入文件后弹出，显示：
  - 原始文本预览（前30行）
  - 识别结果（格式类型、表头行、数据起始行）
  - 用户可手动调整（选择表头行、数据起始行、分隔符）
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QGroupBox, QSpinBox, QRadioButton,
    QButtonGroup, QDialogButtonBox, QSplitter, QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from detector import DetectResult


class DetectDialog(QDialog):
    """格式识别预览 — 用户确认/调整识别结果"""

    def __init__(self, filepath: str, result: DetectResult, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"格式识别 — {filepath.split('/')[-1]}")
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)

        self._filepath = filepath
        self._result = result
        self._final_result = DetectResult(
            format_type=result.format_type,
            confidence=result.confidence,
            encoding=result.encoding,
            separator=result.separator,
            header_row=result.header_row,
            data_start_row=result.data_start_row,
            preamble_lines=result.preamble_lines,
            header_columns=result.header_columns,
            total_lines=result.total_lines,
            sample_lines=result.sample_lines,
            parser_name=result.parser_name,
            extra=result.extra,
        )

        self._setup_ui()
        self._update_preview_highlight()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── 识别结果摘要 ──
        summary_group = QGroupBox("识别结果")
        sg_layout = QVBoxLayout(summary_group)

        self.lbl_summary = QLabel(self._result.description)
        self.lbl_summary.setStyleSheet("font-size:14px; font-weight:600;")
        sg_layout.addWidget(self.lbl_summary)

        info = QLabel(
            f"文件: {self._filepath}\n"
            f"编码: {self._result.encoding}  |  "
            f"总行数: {self._result.total_lines}  |  "
            f"分隔符: {'Tab' if self._result.separator == chr(9) else repr(self._result.separator)}"
        )
        info.setStyleSheet("color:#86868B; font-size:12px;")
        sg_layout.addWidget(info)

        if self._result.preamble_lines:
            pre = QLabel(f"前置说明: {len(self._result.preamble_lines)} 行")
            pre.setStyleSheet("color:#FF9500; font-size:12px;")
            sg_layout.addWidget(pre)

        layout.addWidget(summary_group)

        # ── 手动调整 ──
        adjust_group = QGroupBox("手动调整（如识别有误）")
        ag_layout = QHBoxLayout(adjust_group)

        # 表头行
        hdr_col = QVBoxLayout()
        hdr_col.addWidget(QLabel("表头行号:"))
        self.spin_header = QSpinBox()
        self.spin_header.setRange(-1, 999)
        self.spin_header.setValue(self._result.header_row)
        self.spin_header.setSpecialValueText("无表头")
        self.spin_header.valueChanged.connect(self._on_adjust)
        hdr_col.addWidget(self.spin_header)
        ag_layout.addLayout(hdr_col)

        # 数据起始行
        data_col = QVBoxLayout()
        data_col.addWidget(QLabel("数据起始行:"))
        self.spin_data_start = QSpinBox()
        self.spin_data_start.setRange(0, 999)
        self.spin_data_start.setValue(self._result.data_start_row)
        self.spin_data_start.valueChanged.connect(self._on_adjust)
        data_col.addWidget(self.spin_data_start)
        ag_layout.addLayout(data_col)

        # 分隔符
        sep_col = QVBoxLayout()
        sep_col.addWidget(QLabel("分隔符:"))
        self.combo_sep = QComboBox()
        self.combo_sep.addItems(["Tab", "逗号", "空格", "分号", "自定义..."])
        sep_map = {"\t": 0, ",": 1, " ": 2, ";": 3}
        self.combo_sep.setCurrentIndex(sep_map.get(self._result.separator, 0))
        self.combo_sep.currentIndexChanged.connect(self._on_sep_changed)
        sep_col.addWidget(self.combo_sep)

        self.edit_custom_sep = QComboBox()
        self.edit_custom_sep.setEditable(True)
        self.edit_custom_sep.setVisible(False)
        self.edit_custom_sep.currentTextChanged.connect(self._on_adjust)
        sep_col.addWidget(self.edit_custom_sep)
        ag_layout.addLayout(sep_col)

        # 解析器选择
        parser_col = QVBoxLayout()
        parser_col.addWidget(QLabel("解析器:"))
        self.combo_parser = QComboBox()
        parsers = ["自动", "PMD 热退磁", "DIR 方向数据", "通用表格", "通用文本"]
        self.combo_parser.addItems(parsers)
        parser_map = {"pmd": 1, "dir": 2, "tabular": 3, "generic_text": 4}
        self.combo_parser.setCurrentIndex(parser_map.get(self._result.parser_name, 0))
        parser_col.addWidget(self.combo_parser)
        ag_layout.addLayout(parser_col)

        ag_layout.addStretch()
        layout.addWidget(adjust_group)

        # ── 原始文本预览 ──
        preview_group = QGroupBox("原始文本预览（表头行=蓝色, 数据行=绿色, 说明行=橙色）")
        pv_layout = QVBoxLayout(preview_group)

        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setFont(QFont("Consolas", 11))
        self.text_preview.setPlainText("\n".join(self._result.sample_lines))
        pv_layout.addWidget(self.text_preview)

        layout.addWidget(preview_group, stretch=1)

        # ── 表头列预览 ──
        if self._result.header_columns:
            hdr_preview = QLabel(f"识别到的列名: {' | '.join(self._result.header_columns)}")
            hdr_preview.setStyleSheet("font-size:12px; color:#007AFF; padding:4px;")
            layout.addWidget(hdr_preview)

        # ── 按钮 ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("确认导入")
        ok_btn.setObjectName("btnPrimary")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("取消")
        layout.addWidget(buttons)

    def _on_sep_changed(self, idx):
        self.edit_custom_sep.setVisible(idx == 4)
        self._on_adjust()

    def _on_adjust(self):
        """用户手动调整后更新"""
        self._final_result.header_row = self.spin_header.value()
        self._final_result.data_start_row = self.spin_data_start.value()

        sep_idx = self.combo_sep.currentIndex()
        sep_map = {0: "\t", 1: ",", 2: " ", 3: ";"}
        if sep_idx == 4:
            custom = self.edit_custom_sep.currentText()
            self._final_result.separator = custom if custom else "\t"
        else:
            self._final_result.separator = sep_map.get(sep_idx, "\t")

        parser_idx = self.combo_parser.currentIndex()
        parser_map = {0: None, 1: "pmd", 2: "dir", 3: "tabular", 4: "generic_text"}
        self._final_result.parser_name = parser_map.get(parser_idx)

        self._update_preview_highlight()

    def _update_preview_highlight(self):
        """高亮预览文本：说明行橙色、表头行蓝色、数据行绿色"""
        lines = self._result.sample_lines
        header_row = self._final_result.header_row
        data_start = self._final_result.data_start_row

        self.text_preview.blockSignals(True)
        cursor = self.text_preview.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)

        # 重置格式
        reset_fmt = QTextCharFormat()
        reset_fmt.setBackground(QColor("white"))
        reset_fmt.setForeground(QColor("#1D1D1F"))
        cursor.setCharFormat(reset_fmt)

        # 逐行高亮
        for i, line in enumerate(lines):
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(i):
                cursor.movePosition(QTextCursor.MoveOperation.Down)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)

            fmt = QTextCharFormat()
            if i == header_row:
                fmt.setBackground(QColor("#E3F2FD"))
                fmt.setForeground(QColor("#1565C0"))
            elif i >= data_start:
                fmt.setBackground(QColor("#E8F5E9"))
                fmt.setForeground(QColor("#2E7D32"))
            elif i < data_start:
                fmt.setBackground(QColor("#FFF3E0"))
                fmt.setForeground(QColor("#E65100"))
            cursor.setCharFormat(fmt)

        self.text_preview.blockSignals(False)

    def get_result(self) -> DetectResult:
        return self._final_result
