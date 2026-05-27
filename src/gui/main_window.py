"""
DataForge v1.0 — 通用数据格式转换 + 编辑工作台

核心流程：拖入文件 → 智能识别 → 预览确认 → 列选择/重命名/计算 → 导出/合并
"""

import sys
import os
import json
from pathlib import Path

if getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.join(sys._MEIPASS, "src"))
else:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QTableView, QHeaderView, QFileDialog, QMessageBox, QMenu,
    QToolBar, QStatusBar, QAbstractItemView, QDialog, QInputDialog,
    QComboBox, QLineEdit, QGroupBox, QFormLayout, QTextEdit,
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence, QFont, QColor

import pandas as pd
import numpy as np

from detector import detect, DetectResult
from parsers import ParserRegistry
from pipeline import apply_pipeline, TransformError
from merger import MergeConfig, MergeMode, merge_tables
from undo import UndoStack
from gui.detect_dialog import DetectDialog
from gui.column_panel import ColumnPanel
from gui.sort_dialog import SortDialog
from gui.find_replace_dialog import FindReplaceDialog
from gui.merge_dialog import MergeDialog


# ─── 浅色主题 ─────────────────────────────────────────
APP_STYLE = """
QMainWindow { background-color: #F2F2F7; }
QToolBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E5E5EA;
    padding: 6px 10px; spacing: 12px;
}
QToolBar QToolButton {
    color: #007AFF; background: transparent;
    border: 1px solid transparent; border-radius: 6px;
    padding: 6px 14px; font-size: 13px; font-weight: 500;
}
QToolBar QToolButton:hover { background-color: #E8F0FE; }
QToolBar QToolButton:pressed { background-color: #D2E3FC; }
QLabel { color: #1D1D1F; font-size: 13px; }
QPushButton {
    background-color: #F2F2F7; color: #007AFF;
    border: 1px solid #E5E5EA; border-radius: 8px;
    padding: 8px 18px; font-size: 13px; font-weight: 500;
}
QPushButton:hover { background-color: #E8F0FE; }
QPushButton:pressed { background-color: #D2E3FC; }
QPushButton#btnPrimary {
    background-color: #007AFF; color: #FFFFFF;
    font-weight: 600; border: none;
}
QPushButton#btnPrimary:hover { background-color: #0066D6; }
QPushButton#btnExport {
    background-color: #34C759; color: #FFFFFF;
    font-weight: 600; border: none;
}
QPushButton#btnExport:hover { background-color: #30B350; }
QPushButton:disabled { color: #C7C7CC; background-color: #F2F2F7; }
QListWidget {
    background-color: #FFFFFF; color: #1D1D1F;
    border: 1px solid #E5E5EA; border-radius: 10px;
    font-size: 13px; padding: 6px; outline: none;
}
QListWidget::item { padding: 8px 12px; border-radius: 6px; }
QListWidget::item:selected { background-color: #007AFF; color: #FFFFFF; }
QListWidget::item:hover { background-color: #E8F0FE; }
QTableView {
    background-color: #FFFFFF; color: #1D1D1F;
    border: 1px solid #E5E5EA; border-radius: 10px;
    gridline-color: #F2F2F7; font-size: 13px;
    selection-background-color: #007AFF; selection-color: #FFFFFF;
    alternate-background-color: #F9F9FC;
}
QTableView QHeaderView::section {
    background-color: #F9F9FC; color: #1D1D1F;
    padding: 8px 12px; border: none;
    border-bottom: 2px solid #E5E5EA; font-weight: 600; font-size: 12px;
}
QTableView QHeaderView::section:hover { background-color: #E8F0FE; }
QGroupBox {
    color: #1D1D1F; font-size: 13px; font-weight: 600;
    border: 1px solid #E5E5EA; border-radius: 10px;
    margin-top: 16px; padding: 20px 12px 12px 12px; background-color: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 16px;
    padding: 0 8px; color: #86868B;
}
QComboBox {
    background-color: #FFFFFF; color: #1D1D1F;
    border: 1px solid #E5E5EA; border-radius: 8px;
    padding: 6px 12px; font-size: 13px; min-height: 20px;
}
QLineEdit {
    background-color: #FFFFFF; color: #1D1D1F;
    border: 1px solid #E5E5EA; border-radius: 8px;
    padding: 6px 12px; font-size: 13px;
}
QLineEdit:focus { border-color: #007AFF; }
QTextEdit {
    background-color: #FFFFFF; color: #1D1D1F;
    border: 1px solid #E5E5EA; border-radius: 8px;
}
QStatusBar {
    color: #86868B; background-color: #FFFFFF;
    border-top: 1px solid #E5E5EA; font-size: 12px; padding: 4px 12px;
}
QSplitter::handle { background-color: #E5E5EA; width: 1px; }
QMenuBar {
    background-color: #FFFFFF; color: #1D1D1F;
    border-bottom: 1px solid #E5E5EA; padding: 4px;
}
QMenuBar::item { padding: 6px 12px; border-radius: 6px; }
QMenuBar::item:selected { background-color: #E8F0FE; }
QMenu {
    background-color: #FFFFFF; color: #1D1D1F;
    border: 1px solid #E5E5EA; border-radius: 10px; padding: 6px;
}
QMenu::item { padding: 8px 32px 8px 16px; border-radius: 6px; }
QMenu::item:selected { background-color: #007AFF; color: #FFFFFF; }
QMenu::separator { height: 1px; background-color: #E5E5EA; margin: 4px 8px; }
QScrollArea { border: none; }
"""


# ─── DataFrame Model ──────────────────────────────────
class DataFrameModel(QAbstractTableModel):
    """pandas DataFrame → Qt Table Model（支持编辑 + 排序指示）"""

    def __init__(self, df: pd.DataFrame = None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()
        self._sort_indicators: dict[str, str] = {}

    def set_df(self, df: pd.DataFrame):
        self.beginResetModel()
        self._df = df.reset_index(drop=True)
        self.endResetModel()

    @property
    def df(self):
        return self._df

    def set_sort_indicators(self, indicators: dict):
        self._sort_indicators = indicators
        if self.columnCount() > 0:
            self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, self.columnCount() - 1)

    def rowCount(self, parent=QModelIndex()):
        return len(self._df)

    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            val = self._df.iat[index.row(), index.column()]
            if pd.isna(val):
                return ""
            if isinstance(val, float):
                return f"{val:.6g}"
            return str(val)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole and index.isValid():
            col = self._df.columns[index.column()]
            row_label = self._df.index[index.row()]
            try:
                self._df.loc[row_label, col] = value
            except (ValueError, TypeError):
                self._df[col] = self._df[col].astype(object)
                self._df.loc[row_label, col] = value
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
            return True
        return False

    def flags(self, index: QModelIndex):
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                col_name = str(self._df.columns[section])
                indicator = self._sort_indicators.get(col_name, "")
                if indicator == "asc":
                    return f"{col_name}  ▲"
                elif indicator == "desc":
                    return f"{col_name}  ▼"
                return col_name
            else:
                return str(section + 1)
        return None

    def removeRows(self, positions: list[int]):
        positions = sorted(set(positions), reverse=True)
        for row in positions:
            if 0 <= row < len(self._df):
                self.beginRemoveRows(QModelIndex(), row, row)
                self._df.drop(self._df.index[row], inplace=True)
                self._df.reset_index(drop=True, inplace=True)
                self.endRemoveRows()


# ─── 主窗口 ───────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DataForge — 数据格式转换工作台")
        self.setMinimumSize(1400, 850)

        self._loaded_files: dict[str, tuple[pd.DataFrame, DetectResult]] = {}  # path → (df, detect_result)
        self._current_model = DataFrameModel()
        self._undo_stack = UndoStack()
        self._sort_state: dict[str, str] = {}

        # 预设目录
        if getattr(sys, "frozen", False):
            self._presets_dir = Path(sys.executable).parent / "presets"
        else:
            self._presets_dir = Path(__file__).resolve().parent.parent.parent / "presets"
        self._presets_dir.mkdir(exist_ok=True)

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_shortcuts()

        self.statusBar().showMessage("就绪 — 拖拽文件到左侧面板或点击「导入文件」开始")

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：文件面板
        self.file_panel = self._create_file_panel()
        main_splitter.addWidget(self.file_panel)

        # 中间：表格视图
        self.table_view = self._create_table_view()
        main_splitter.addWidget(self.table_view)

        # 右侧：列操作面板
        self.column_panel = ColumnPanel()
        self.column_panel.columns_changed.connect(self._apply_column_selection)
        self.column_panel.compute_requested.connect(self._add_compute_column)
        main_splitter.addWidget(self.column_panel)

        main_splitter.setSizes([280, 750, 300])

        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(main_splitter)

    def _create_file_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        lbl = QLabel("📁 文件列表")
        lbl.setStyleSheet("font-size:15px; font-weight:700; color:#1D1D1F;")
        layout.addWidget(lbl)

        self.file_list = QListWidget()
        self.file_list.setAcceptDrops(True)
        self.file_list.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.dragEnterEvent = self._drag_enter
        self.file_list.dropEvent = self._drop_event
        self.file_list.itemClicked.connect(self._on_file_selected)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._file_context_menu)
        layout.addWidget(self.file_list)

        btn_row = QHBoxLayout()
        btn_import = QPushButton("📥 导入文件")
        btn_import.setObjectName("btnPrimary")
        btn_import.clicked.connect(self._import_files)
        btn_clear = QPushButton("🗑 清空")
        btn_clear.clicked.connect(self._clear_files)
        btn_row.addWidget(btn_import)
        btn_row.addWidget(btn_clear)
        layout.addLayout(btn_row)

        # 合并按钮
        btn_merge = QPushButton("🔗 合并文件")
        btn_merge.setObjectName("btnExport")
        btn_merge.clicked.connect(self._merge_files)
        layout.addWidget(btn_merge)

        # 导出按钮
        btn_export = QPushButton("📤 导出当前表格")
        btn_export.setObjectName("btnExport")
        btn_export.clicked.connect(self._export_data)
        layout.addWidget(btn_export)

        # 信息
        self.lbl_file_info = QLabel("")
        self.lbl_file_info.setStyleSheet("color:#86868B; font-size:11px; padding:4px;")
        self.lbl_file_info.setWordWrap(True)
        layout.addWidget(self.lbl_file_info)

        fmt_lbl = QLabel("支持: PMD, DIR, CSV, TSV, TXT, XLSX, 任意文本")
        fmt_lbl.setStyleSheet("color:#86868B; font-size:11px; padding:4px;")
        layout.addWidget(fmt_lbl)

        return panel

    def _create_table_view(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        lbl = QLabel("📊 数据表格")
        lbl.setStyleSheet("font-size:15px; font-weight:700; color:#1D1D1F;")
        header_row.addWidget(lbl)
        header_row.addStretch()
        self.lbl_row_count = QLabel("0 行")
        self.lbl_row_count.setStyleSheet("color:#86868B;")
        header_row.addWidget(self.lbl_row_count)
        layout.addLayout(header_row)

        self.table = QTableView()
        self.table.setModel(self._current_model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_sort)
        self.table.setShowGrid(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_context_menu)
        layout.addWidget(self.table)

        # 底部操作栏
        btn_row = QHBoxLayout()
        btn_del = QPushButton("删除选中行")
        btn_del.clicked.connect(self._delete_selected_rows)
        btn_fill = QPushButton("⬇ 向下填充")
        btn_fill.clicked.connect(self._fill_down)
        btn_undo = QPushButton("↩ 撤销")
        btn_undo.clicked.connect(self._undo)
        btn_redo = QPushButton("↪ 重做")
        btn_redo.clicked.connect(self._redo)
        btn_row.addWidget(btn_del)
        btn_row.addWidget(btn_fill)
        btn_row.addWidget(btn_undo)
        btn_row.addWidget(btn_redo)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._current_model.modelReset.connect(self._update_row_label)
        return panel

    # ── 快捷键 ──────────────────────────────────────
    def _setup_shortcuts(self):
        pass  # 在 _setup_menu 中通过 QKeySequence 设置

    # ── 菜单栏 ──────────────────────────────────────
    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("导入文件...", QKeySequence("Ctrl+O"), self._import_files)
        file_menu.addAction("清空文件", self._clear_files)
        file_menu.addSeparator()
        file_menu.addAction("导出当前表格...", QKeySequence("Ctrl+S"), self._export_data)
        file_menu.addSeparator()
        file_menu.addAction("退出", QKeySequence("Ctrl+Q"), self.close)

        edit_menu = menubar.addMenu("编辑(&E)")
        edit_menu.addAction("撤销", QKeySequence("Ctrl+Z"), self._undo)
        edit_menu.addAction("重做", QKeySequence("Ctrl+Y"), self._redo)
        edit_menu.addSeparator()
        edit_menu.addAction("向下填充", QKeySequence("Ctrl+D"), self._fill_down)
        edit_menu.addAction("删除选中行", QKeySequence("Delete"), self._delete_selected_rows)
        edit_menu.addSeparator()
        edit_menu.addAction("查找和替换...", QKeySequence("Ctrl+F"), self._open_find_replace)
        edit_menu.addAction("排序...", QKeySequence("Ctrl+Shift+O"), self._open_sort_dialog)

        tools_menu = menubar.addMenu("工具(&T)")
        tools_menu.addAction("合并文件...", QKeySequence("Ctrl+M"), self._merge_files)

        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("关于 DataForge", self._show_about)

    def _setup_toolbar(self):
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)

        def _add(text, slot, tip=""):
            act = QAction(text, toolbar)
            act.triggered.connect(slot)
            if tip:
                act.setToolTip(tip)
            toolbar.addAction(act)

        _add("📥 导入", self._import_files, "导入文件 (Ctrl+O)")
        _add("🗑 清空", self._clear_files, "清空所有文件")
        toolbar.addSeparator()
        _add("⬇ 填充", self._fill_down, "向下填充 (Ctrl+D)")
        _add("✕ 删行", self._delete_selected_rows, "删除选中行")
        toolbar.addSeparator()
        _add("↩ 撤销", self._undo, "撤销 (Ctrl+Z)")
        _add("↪ 重做", self._redo, "重做 (Ctrl+Y)")
        toolbar.addSeparator()
        _add("🔄 排序", self._open_sort_dialog, "排序 (Ctrl+Shift+O)")
        _add("🔍 查找", self._open_find_replace, "查找替换 (Ctrl+F)")
        toolbar.addSeparator()
        _add("🔗 合并", self._merge_files, "合并文件 (Ctrl+M)")
        _add("📤 导出", self._export_data, "导出 (Ctrl+S)")

    # ── 文件操作 ─────────────────────────────────────
    def _drag_enter(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self._load_file(path)

    def _import_files(self):
        extensions = " ".join(f"*.{e}" for e in ParserRegistry.supported_extensions())
        filter_str = f"所有支持文件 ({extensions} *.pmd *.dir);;所有文件 (*.*)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", filter_str)
        if not files:
            return

        if len(files) == 1:
            # 单文件：正常流程
            self._load_file(files[0])
        else:
            # 批量：第一个确认，其余自动套用
            self._batch_load_files(files)

    def _load_file(self, path: str):
        if path in self._loaded_files:
            return

        try:
            # 1. 智能识别
            result = detect(path)

            # 2. 弹出识别预览对话框
            dlg = DetectDialog(path, result, parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            final_result = dlg.get_result()

            # 3. 用识别结果解析（三级容错）
            parser_name = final_result.parser_name
            kwargs = {
                "encoding": final_result.encoding,
                "separator": final_result.separator,
                "header_row": final_result.header_row,
                "data_start_row": final_result.data_start_row,
                "header_columns": final_result.header_columns,
            }

            df = None
            errors = []

            # 尝试1: 推荐解析器
            if parser_name:
                parser = ParserRegistry.get_by_name(parser_name)
                if parser:
                    try:
                        df = parser.parse(path, **kwargs)
                    except Exception as e1:
                        errors.append(f"[{parser_name}] {e1}")

            # 尝试2: 按扩展名自动
            if df is None:
                try:
                    df = ParserRegistry.parse_file(path, **kwargs)
                except Exception as e2:
                    errors.append(f"[auto] {e2}")

            # 尝试3: 通用文本兜底
            if df is None:
                fallback = ParserRegistry.get_by_name("generic_text")
                if fallback:
                    try:
                        df = fallback.parse(path, **kwargs)
                    except Exception as e3:
                        errors.append(f"[generic_text] {e3}")

            if df is None or df.empty:
                raise ValueError(
                    "所有解析器均未提取到数据:\n" + "\n".join(f"  {e}" for e in errors)
                )

            # 4. 存储
            self._loaded_files[path] = (df, final_result)
            name = os.path.basename(path)
            item = QListWidgetItem(f"  {name}  ({len(df)} 行)")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(f"{path}\n{len(df)} 行, {len(df.columns)} 列\n格式: {final_result.description}")
            self.file_list.addItem(item)

            # 5. 显示到表格
            self._set_current_data(df)
            self.statusBar().showMessage(f"已导入: {name} ({len(df)} 行, 格式: {final_result.format_type})")

        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"无法解析文件:\n{path}\n\n{str(e)}")

    def _batch_load_files(self, files: list[str]):
        """批量导入：第一个文件确认格式，其余自动套用"""
        if not files:
            return

        # 1. 识别第一个文件
        first = files[0]
        result = detect(first)

        # 2. 弹出确认（显示批量数量）
        dlg = DetectDialog(first, result, parent=self)
        dlg.setWindowTitle(f"批量导入 {len(files)} 个文件 — 确认格式（第一个文件）")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        final_result = dlg.get_result()

        # 3. 准备解析参数
        kwargs = {
            "encoding": final_result.encoding,
            "separator": final_result.separator,
            "header_row": final_result.header_row,
            "data_start_row": final_result.data_start_row,
            "header_columns": final_result.header_columns,
        }
        parser_name = final_result.parser_name
        parser = ParserRegistry.get_by_name(parser_name) if parser_name else None

        # 4. 逐个解析
        success = 0
        fail = 0
        for path in files:
            if path in self._loaded_files:
                continue
            try:
                df = None
                # 尝试推荐解析器
                if parser:
                    try:
                        df = parser.parse(path, **kwargs)
                    except Exception:
                        pass
                # 降级
                if df is None:
                    try:
                        df = ParserRegistry.parse_file(path, **kwargs)
                    except Exception:
                        pass
                if df is None:
                    fallback = ParserRegistry.get_by_name("generic_text")
                    if fallback:
                        df = fallback.parse(path, **kwargs)

                if df is not None and not df.empty:
                    self._loaded_files[path] = (df, final_result)
                    name = os.path.basename(path)
                    item = QListWidgetItem(f"  {name}  ({len(df)} 行)")
                    item.setData(Qt.ItemDataRole.UserRole, path)
                    item.setToolTip(f"{path}\n{len(df)} 行, {len(df.columns)} 列")
                    self.file_list.addItem(item)
                    success += 1
                else:
                    fail += 1
            except Exception:
                fail += 1

        # 5. 显示最后一个文件的数据
        if success > 0:
            last_path = [p for p in files if p in self._loaded_files]
            if last_path:
                df, _ = self._loaded_files[last_path[-1]]
                self._set_current_data(df)

        self.statusBar().showMessage(
            f"批量导入完成: {success} 成功" + (f", {fail} 失败" if fail else "")
        )

    def _on_file_selected(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path in self._loaded_files:
            df, _ = self._loaded_files[path]
            self._set_current_data(df.copy())

    def _clear_files(self):
        self._loaded_files.clear()
        self.file_list.clear()
        self._current_model.set_df(pd.DataFrame())
        self.column_panel.set_columns([])
        self._undo_stack.clear()
        self._sort_state.clear()

    def _file_context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        if not item:
            return
        menu = QMenu()
        remove_action = menu.addAction("🗑 移除")
        remove_action.triggered.connect(lambda: self._remove_file(item))
        menu.addSeparator()
        clear_all = menu.addAction("清空全部")
        clear_all.triggered.connect(self._clear_files)
        menu.exec(self.file_list.mapToGlobal(pos))

    def _remove_file(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        self._loaded_files.pop(path, None)
        row = self.file_list.row(item)
        self.file_list.takeItem(row)

    # ── 数据操作 ─────────────────────────────────────
    def _set_current_data(self, df: pd.DataFrame):
        self._current_model.set_df(df)
        self.column_panel.set_columns(df.columns.tolist())
        self._undo_stack.clear()
        self._sort_state.clear()
        self._current_model.set_sort_indicators({})
        self._update_row_label()

    def _apply_column_selection(self, selected_cols: list[str]):
        """应用列选择（来自 ColumnPanel）"""
        df = self._current_model.df
        if df.empty:
            return

        # 保存撤销
        self._undo_stack.push("列选择", df.copy())

        # 应用重命名
        renames = self.column_panel.get_renames()
        if renames:
            df = df.rename(columns=renames)

        # 选择列
        available = [c for c in selected_cols if c in df.columns]
        if available:
            df = df[available].copy()

        self._current_model.set_df(df)
        self.column_panel.set_columns(df.columns.tolist())
        self._update_row_label()
        self.statusBar().showMessage(f"列选择已应用: {len(available)} 列")

    def _add_compute_column(self, name: str, formula: str):
        """添加计算列"""
        df = self._current_model.df
        if df.empty:
            return

        self._undo_stack.push(f"计算列 {name}", df.copy())

        try:
            from pipeline import apply_pipeline
            result = apply_pipeline(df, [{"type": "compute_column", "name": name, "formula": formula}])
            self._current_model.set_df(result)
            self.column_panel.set_columns(result.columns.tolist())
            self.statusBar().showMessage(f"已添加计算列: {name}")
        except TransformError as e:
            QMessageBox.warning(self, "计算列失败", str(e))

    def _delete_selected_rows(self):
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        self._undo_stack.push("删除行", self._current_model.df.copy())
        rows = [idx.row() for idx in selection]
        self._current_model.removeRows(rows)
        self._update_row_label()
        self.statusBar().showMessage(f"已删除 {len(rows)} 行")

    def _fill_down(self):
        selection = self.table.selectionModel().selection()
        if not selection:
            return

        self._undo_stack.push("向下填充", self._current_model.df.copy())

        rows_by_col: dict[int, list[int]] = {}
        col_min_row: dict[int, int] = {}
        for idx in selection.indexes():
            col = idx.column()
            row = idx.row()
            if col not in rows_by_col:
                rows_by_col[col] = []
                col_min_row[col] = row
            rows_by_col[col].append(row)
            if row < col_min_row[col]:
                col_min_row[col] = row

        df = self._current_model.df
        for col, rows in rows_by_col.items():
            src_row = col_min_row[col]
            targets = [r for r in rows if r != src_row]
            if targets:
                val = df.iat[src_row, col]
                col_name = df.columns[col]
                top = min(targets)
                bottom = max(targets)
                try:
                    df.loc[top:bottom, col_name] = val
                except (ValueError, TypeError):
                    df[col_name] = df[col_name].astype(object)
                    df.loc[top:bottom, col_name] = val

        self._current_model.set_df(df)
        self.statusBar().showMessage("向下填充完成")

    def _undo(self):
        df, desc = self._undo_stack.undo(self._current_model.df)
        self._current_model.set_df(df)
        self.column_panel.set_columns(df.columns.tolist())
        self.statusBar().showMessage(f"撤销: {desc}")

    def _redo(self):
        df, desc = self._undo_stack.redo(self._current_model.df)
        self._current_model.set_df(df)
        self.column_panel.set_columns(df.columns.tolist())
        self.statusBar().showMessage(f"重做: {desc}")

    def _update_row_label(self, *args):
        self.lbl_row_count.setText(f"{self._current_model.rowCount()} 行")

    # ── 表格右键菜单 ────────────────────────────────
    def _table_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("⬇ 向下填充\tCtrl+D", self._fill_down)
        menu.addSeparator()
        menu.addAction("🔄 排序...", self._open_sort_dialog)
        menu.addAction("🔍 查找替换...", self._open_find_replace)
        menu.addSeparator()
        menu.addAction("🗑 删除选中行\tDelete", self._delete_selected_rows)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    # ── 表头排序 ─────────────────────────────────────
    def _on_header_sort(self, logical_index: int):
        df = self._current_model.df
        if df.empty or logical_index >= len(df.columns):
            return

        self._undo_stack.push("排序", df.copy())

        col_name = df.columns[logical_index]
        current = self._sort_state.get(col_name)

        if current is None or current == "none":
            sorted_df = df.sort_values(by=col_name, ascending=True, na_position="last", kind="mergesort")
            self._sort_state = {col_name: "asc"}
        elif current == "asc":
            sorted_df = df.sort_values(by=col_name, ascending=False, na_position="last", kind="mergesort")
            self._sort_state = {col_name: "desc"}
        else:
            sorted_df = df
            self._sort_state = {}

        self._current_model.set_df(sorted_df)
        self._current_model.set_sort_indicators(self._sort_state)
        state_text = {"asc": "升序", "desc": "降序"}.get(self._sort_state.get(col_name, ""), "恢复")
        self.statusBar().showMessage(f"「{col_name}」→ {state_text}")

    # ── 排序/查找对话框 ──────────────────────────────
    def _open_sort_dialog(self):
        df = self._current_model.df
        if df.empty:
            return
        dlg = SortDialog(df, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._undo_stack.push("排序", df.copy())
            self._current_model.set_df(dlg.get_sorted_df())
            self._sort_state.clear()
            self._current_model.set_sort_indicators({})

    def _open_find_replace(self):
        df = self._current_model.df
        if df.empty:
            return
        dlg = FindReplaceDialog(df, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._undo_stack.push("查找替换", df.copy())
            self._current_model.set_df(dlg.get_result_df())
            self.column_panel.set_columns(dlg.get_result_df().columns.tolist())

    # ── 合并向导 ─────────────────────────────────────
    def _merge_files(self):
        if len(self._loaded_files) < 2:
            QMessageBox.information(self, "文件不足", "请先导入至少 2 个文件")
            return

        file_dfs = {path: df for path, (df, _) in self._loaded_files.items()}
        dlg = MergeDialog(file_dfs, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result_df = dlg.get_result_df()
            if result_df is not None:
                self._undo_stack.push("合并", self._current_model.df.copy())
                self._set_current_data(result_df)
                self.statusBar().showMessage(f"合并完成: {len(result_df)} 行")

    # ── 导出 ─────────────────────────────────────────
    def _export_data(self):
        df = self._current_model.df
        if df.empty:
            QMessageBox.information(self, "无数据", "表格中没有数据")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "",
            "Excel 文件 (*.xlsx);;CSV 文件 (*.csv);;文本文件 (*.txt);;PMD 文件 (*.pmd)"
        )
        if not file_path:
            return

        try:
            ext = file_path.rsplit(".", 1)[-1].lower()
            if ext == "xlsx":
                df.to_excel(file_path, index=False, engine="openpyxl")
            elif ext == "csv":
                df.to_csv(file_path, index=False, encoding="utf-8-sig")
            elif ext == "txt":
                df.to_csv(file_path, index=False, sep="\t", encoding="utf-8-sig")
            elif ext == "pmd":
                self._export_pmd(df, file_path)
            else:
                df.to_csv(file_path, index=False, sep="\t", encoding="utf-8-sig")

            self.statusBar().showMessage(f"导出成功: {file_path} ({len(df)} 行)")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def _export_pmd(self, df: pd.DataFrame, path: str):
        """导出为 PMD 格式"""
        with open(path, "w", encoding="utf-8") as f:
            # 写 specimen 信息行
            specimen = "DataForge_Export"
            if "specimen" in df.columns:
                specimen = str(df["specimen"].iloc[0]) if len(df) > 0 else specimen
            f.write(f"{specimen}  a=0.0  b=0.0  s=0.0  d=0.0  v=1.0E-6m3\n")

            # 写表头
            f.write(" PAL  Xc (Am2)  Yc (Am2)  Zc (Am2)  MAG(A/m)   Dg    Ig    Ds    Is   a95\n")

            # 写数据行
            for _, row in df.iterrows():
                treatment = int(row.get("treatment", 0))
                xc = float(row.get("xc", 0.0))
                yc = float(row.get("yc", 0.0))
                zc = float(row.get("zc", 0.0))
                mag = float(row.get("MAG", 0.0))
                dg = float(row.get("Dg", 0.0))
                ig = float(row.get("Ig", 0.0))
                ds = float(row.get("Ds", 0.0))
                is_ = float(row.get("Is", 0.0))
                a95 = float(row.get("a95", 0.0))
                f.write(f"{treatment:4d} {xc:11.2E} {yc:11.2E} {zc:11.2E} {mag:9.2E} {dg:6.1f} {ig:6.1f} {ds:6.1f} {is_:6.1f} {a95:5.1f}\n")

    def _show_about(self):
        QMessageBox.about(
            self, "关于 DataForge",
            "DataForge v1.0\n\n"
            "通用数据格式转换 + 编辑工作台\n\n"
            "功能:\n"
            "  • 智能格式识别（不靠扩展名）\n"
            "  • PMD / DIR / CSV / TSV / XLSX / 任意文本\n"
            "  • 列选择 + 重命名 + 计算列\n"
            "  • 排序 / 查找替换 / 向下填充\n"
            "  • 撤销 / 重做\n"
            "  • 多文件合并（纵向追加 / 横向匹配合并）\n"
            "  • 导出为 XLSX / CSV / TXT / PMD\n\n"
            "技术栈: Python + PyQt6 + pandas + openpyxl\n\n"
            "© 2026 DataForge"
        )


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    app.setApplicationName("DataForge")
    app.setApplicationDisplayName("DataForge")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
