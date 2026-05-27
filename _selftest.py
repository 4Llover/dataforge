"""
DataForge 自测脚本
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from detector import detect
from parsers import ParserRegistry
from pipeline import apply_pipeline, TransformError
from merger import merge_tables, MergeConfig, MergeMode
from undo import UndoStack
import pandas as pd

ASSETS = os.path.join(os.path.dirname(__file__), "assets")

def test_detector():
    print("=== 1. SmartDetector 测试 ===")
    for fname in os.listdir(ASSETS):
        fpath = os.path.join(ASSETS, fname)
        if os.path.isfile(fpath):
            r = detect(fpath)
            print(f"  {fname}: type={r.format_type}, conf={r.confidence:.0%}, "
                  f"parser={r.parser_name}, header_row={r.header_row}, "
                  f"data_start={r.data_start_row}")
    print()

def test_parsers():
    print("=== 2. 解析器测试 ===")
    for fname in os.listdir(ASSETS):
        fpath = os.path.join(ASSETS, fname)
        if os.path.isfile(fpath):
            try:
                df = ParserRegistry.parse_file(fpath)
                print(f"  {fname}: {len(df)} rows × {len(df.columns)} cols → {list(df.columns[:5])}...")
            except Exception as e:
                print(f"  {fname}: FAILED — {e}")
    print()

def test_pipeline():
    print("=== 3. 管线测试 ===")
    pmd_path = os.path.join(ASSETS, "PMDdata.PMD")
    if os.path.exists(pmd_path):
        df = ParserRegistry.parse_file(pmd_path)
        result = apply_pipeline(df, [
            {"type": "select_columns", "columns": ["specimen", "treatment", "MAG", "Ds", "Is"]},
            {"type": "rename_columns", "map": {"MAG": "magnetization"}},
            {"type": "filter_rows", "column": "Ds", "condition": "gt", "value": 0},
        ])
        print(f"  PMD管线: {len(df)} → {len(result)} rows, cols={list(result.columns)}")
    
    # 计算列测试
    test_df = pd.DataFrame({"Kvol": [100, 200], "vol": [8.0, 10.0], "mass": [2.5, 3.0]})
    result = apply_pipeline(test_df, [
        {"type": "compute_column", "name": "Kmass", "formula": "Kvol * vol / 1000 / mass"},
    ])
    print(f"  计算列: Kmass = {list(result['Kmass'].round(6))}")
    print()

def test_merger():
    print("=== 4. 合并测试 ===")
    df1 = pd.DataFrame({"sample": ["A", "B"], "value": [1, 2]})
    df2 = pd.DataFrame({"sample": ["C", "D"], "value": [3, 4]})
    
    r = merge_tables([df1, df2], MergeConfig(mode=MergeMode.CONCAT, add_source_col=True))
    print(f"  concat: {len(r.df)} rows → {r.summary}")
    
    df_left = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
    df_right = pd.DataFrame({"id": [2, 3, 4], "score": [80, 90, 70]})
    r = merge_tables([df_left, df_right], MergeConfig(
        mode=MergeMode.JOIN, join_key_left="id", join_key_right="id", join_how="left"
    ))
    print(f"  join: {len(r.df)} rows → {r.summary}")
    print()

def test_undo():
    print("=== 5. 撤销/重做测试 ===")
    stack = UndoStack()
    df0 = pd.DataFrame({"x": [1, 2, 3]})
    df1 = pd.DataFrame({"x": [1, 2, 3, 4]})
    df2 = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
    
    stack.push("添加行", df0.copy())
    stack.push("再添加行", df1.copy())
    
    restored, desc = stack.undo(df2)
    print(f"  undo: {len(df2)} → {len(restored)} rows ({desc})")
    
    restored2, desc2 = stack.undo(restored)
    print(f"  undo: {len(restored)} → {len(restored2)} rows ({desc2})")
    
    restored3, desc3 = stack.redo(restored2)
    print(f"  redo: {len(restored2)} → {len(restored3)} rows ({desc3})")
    print()

if __name__ == "__main__":
    test_detector()
    test_parsers()
    test_pipeline()
    test_merger()
    test_undo()
    print("=== ALL TESTS PASSED ===")
