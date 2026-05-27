"""
DataForge v1.0 — 通用数据格式转换 + 编辑工作台
启动脚本
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
if getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.join(sys._MEIPASS, "src"))
else:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gui.main_window import main

if __name__ == "__main__":
    main()
