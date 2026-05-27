# -*- mode: python ; coding: utf-8 -*-
"""
DataForge PyInstaller 打包配置
"""

import os
import sys

block_cipher = None

# 项目根目录
ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(ROOT, 'run.py')],
    pathex=[os.path.join(ROOT, 'src')],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'presets'), 'presets'),
        (os.path.join(ROOT, 'assets'), 'assets'),
    ],
    hiddenimports=[
        'pandas',
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.groupby',
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.styles',
        'numpy',
        'numpy.core._methods',
        'numpy.lib.format',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        # src 内部模块
        'detector',
        'pipeline',
        'merger',
        'undo',
        'matcher',
        'parsers',
        'parsers.base',
        'parsers.pmd',
        'parsers.dir',
        'parsers.tabular',
        'parsers.generic_text',
        'gui',
        'gui.main_window',
        'gui.detect_dialog',
        'gui.column_panel',
        'gui.sort_dialog',
        'gui.find_replace_dialog',
        'gui.merge_dialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DataForge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # 保留控制台窗口看错误信息
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DataForge',
)
