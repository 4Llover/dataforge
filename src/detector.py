"""
SmartDetector — 基于内容的格式智能识别

不靠文件扩展名，靠内容特征逐层检测：
1. 特征行匹配（PMD/DIR 的特征标记）
2. 结构分析（表头行/数据行/前置说明）
3. 分隔符推断（Tab/逗号/空格/固定宽度）
4. 编码检测
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DetectResult:
    """格式识别结果"""
    format_type: str = "unknown"         # pmd / dir / tabular / generic
    confidence: float = 0.0              # 0~1 置信度
    encoding: str = "utf-8"              # 检测到的编码
    separator: str = "\t"                # 分隔符
    header_row: int = -1                 # 表头行号（0-indexed, -1=无表头）
    data_start_row: int = 0              # 数据起始行号
    preamble_lines: list[str] = field(default_factory=list)  # 前置说明行
    header_columns: list[str] = field(default_factory=list)  # 表头列名
    total_lines: int = 0
    sample_lines: list[str] = field(default_factory=list)    # 前20行原始文本
    parser_name: str = "generic_text"    # 推荐的解析器名
    extra: dict = field(default_factory=dict)  # 额外信息（如 PMD 的 specimen）

    @property
    def description(self) -> str:
        labels = {
            "pmd": "PMD 热退磁数据",
            "dir": "DIR 方向数据",
            "tabular": "表格数据 (CSV/TSV/Excel)",
            "generic_text": "通用文本数据",
        }
        label = labels.get(self.format_type, "未知格式")
        return f"{label} (置信度 {self.confidence:.0%})"


# ── 编码检测 ──────────────────────────────────────────────
_ENCODINGS = ["utf-8", "gbk", "gb2312", "latin-1", "utf-16"]


def _try_read(filepath: str, encoding: str, max_bytes: int = 32768) -> Optional[str]:
    try:
        with open(filepath, "r", encoding=encoding, errors="strict") as f:
            return f.read(max_bytes)
    except (UnicodeDecodeError, UnicodeError):
        return None


def _detect_encoding(filepath: str) -> tuple[str, str]:
    """返回 (encoding, text)"""
    for enc in _ENCODINGS:
        text = _try_read(filepath, enc)
        if text is not None:
            return enc, text
    # fallback
    with open(filepath, "r", encoding="latin-1", errors="replace") as f:
        return "latin-1", f.read(32768)


# ── 特征匹配 ──────────────────────────────────────────────
_PMD_HEADER_RE = re.compile(
    r"Xc\s*\(Am2\)|Yc\s*\(Am2\)|Zc\s*\(Am2\)|MAG\s*\(A/m\)|MAG\(A/m\)",
    re.IGNORECASE,
)
_PMD_SPECIMEN_RE = re.compile(
    r"^(\S+)\s+a=\s*[\d.]+\s+b=\s*[\d.]+\s+s=\s*[\d.]+\s+d=\s*[\d.]+"
)
_DIR_LINE_RE = re.compile(r"\s(ht|lt)\s*$", re.IGNORECASE)


def _detect_pmd(lines: list[str]) -> Optional[DetectResult]:
    """检测 PMD 格式"""
    for i, line in enumerate(lines):
        if _PMD_HEADER_RE.search(line):
            # 找到表头行，往上找 specimen 行
            specimen = ""
            for j in range(i - 1, -1, -1):
                m = _PMD_SPECIMEN_RE.match(lines[j].strip())
                if m:
                    specimen = m.group(1)
                    break
            # 解析表头列
            header_cols = _parse_pmd_header(line)
            return DetectResult(
                format_type="pmd",
                confidence=0.95,
                header_row=i,
                data_start_row=i + 1,
                header_columns=header_cols,
                parser_name="pmd",
                extra={"specimen": specimen},
            )
    return None


def _parse_pmd_header(line: str) -> list[str]:
    """解析 PMD 表头行"""
    # 标准列名映射
    col_map = {
        "PAL": "treatment",
        "Xc": "xc", "Yc": "yc", "Zc": "zc",
        "MAG": "MAG", "Dg": "Dg", "Ig": "Ig",
        "Ds": "Ds", "Is": "Is", "a95": "a95",
    }
    cols = []
    parts = line.split()
    for p in parts:
        clean = re.sub(r"\(.*?\)", "", p).strip()
        if clean in col_map:
            cols.append(col_map[clean])
        elif clean:
            cols.append(clean)
    return cols


def _detect_dir(lines: list[str]) -> Optional[DetectResult]:
    """检测 DIR 格式"""
    dir_count = 0
    total_data = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == "\x1a":
            continue
        parts = stripped.split()
        if len(parts) >= 9:
            total_data += 1
            if _DIR_LINE_RE.search(stripped):
                dir_count += 1
    if total_data > 0 and dir_count / total_data > 0.8:
        return DetectResult(
            format_type="dir",
            confidence=0.90,
            header_row=-1,  # DIR 没有表头行
            data_start_row=0,
            header_columns=["SampleID", "treatment", "N", "Dg", "Ig", "Ds", "Is", "a95", "type"],
            parser_name="dir",
        )
    return None


# ── 表格/通用文本检测 ─────────────────────────────────────
def _detect_separator(lines: list[str]) -> tuple[str, float]:
    """推断最佳分隔符，返回 (separator, consistency_score)"""
    candidates = [
        ("\t", None),
        (",", None),
        (";", None),
        ("|", None),
    ]
    best_sep = "\t"
    best_score = 0.0

    for sep, _ in candidates:
        col_counts = []
        for line in lines:
            stripped = line.strip()
            if stripped and stripped != "\x1a":
                count = len(stripped.split(sep))
                col_counts.append(count)
        if not col_counts:
            continue
        # 计算一致性：众数占比
        from collections import Counter
        counter = Counter(col_counts)
        mode_count = counter.most_common(1)[0][1]
        score = mode_count / len(col_counts)
        if score > best_score:
            best_score = score
            best_sep = sep

    return best_sep, best_score


def _detect_header_and_preamble(lines: list[str], sep: str) -> tuple[int, int, list[str], list[str]]:
    """
    检测表头行和前置说明
    
    返回: (header_row, data_start_row, preamble_lines, header_columns)
    """
    # 跳过空行找起始
    non_empty_start = 0
    for i, line in enumerate(lines):
        if line.strip() and line.strip() != "\x1a":
            non_empty_start = i
            break

    # 逐行分析：数值密度
    def numeric_ratio(line: str) -> float:
        parts = line.strip().split(sep) if sep else [line.strip()]
        if not parts:
            return 0.0
        numeric = 0
        for p in parts:
            p = p.strip()
            if not p:
                continue
            try:
                float(p.replace("E+", "e+").replace("E-", "e-"))
                numeric += 1
            except ValueError:
                pass
        return numeric / max(len(parts), 1)

    # 找第一个高数值密度行 → 那就是数据起始
    # 表头行 = 数据起始行的上一行（如果它看起来像表头）
    data_start = -1
    for i in range(non_empty_start, len(lines)):
        line = lines[i].strip()
        if not line or line == "\x1a":
            continue
        ratio = numeric_ratio(line)
        if ratio >= 0.5:  # 超过一半是数值 → 数据行
            data_start = i
            break

    if data_start < 0:
        # 没找到明显的数据行，整个文件都是文本
        return -1, non_empty_start, [], []

    # 检查 data_start 之前是否有表头行
    header_row = -1
    header_cols = []
    preamble = []

    for i in range(non_empty_start, data_start):
        line = lines[i].strip()
        if not line or line == "\x1a":
            continue
        nr = numeric_ratio(line)
        if nr < 0.3:
            # 可能是表头或说明
            parts = line.split(sep) if sep else line.split()
            # 表头行的特征：列数 >= 3 且与数据行列数接近
            data_parts = lines[data_start].strip().split(sep) if sep else lines[data_start].strip().split()
            if len(parts) >= 3 and abs(len(parts) - len(data_parts)) <= 2:
                header_row = i
                header_cols = [p.strip() for p in parts]
            else:
                preamble.append(line)
        else:
            preamble.append(line)

    return header_row, data_start, preamble, header_cols


def _detect_tabular(lines: list[str], sep: str, sep_score: float) -> Optional[DetectResult]:
    """检测通用表格格式"""
    if sep_score < 0.6:
        return None
    header_row, data_start, preamble, header_cols = _detect_header_and_preamble(lines, sep)
    return DetectResult(
        format_type="tabular",
        confidence=sep_score,
        separator=sep,
        header_row=header_row,
        data_start_row=data_start,
        preamble_lines=preamble,
        header_columns=header_cols,
        parser_name="tabular",
    )


# ── 主检测函数 ─────────────────────────────────────────────
def detect(filepath: str) -> DetectResult:
    """
    智能检测文件格式
    
    优先级：PMD > DIR > 表格 > 通用文本
    """
    encoding, text = _detect_encoding(filepath)
    lines = text.splitlines()
    if not lines:
        return DetectResult(encoding=encoding, sample_lines=[])

    sample = lines[:30]  # 前30行用于检测

    # 1. PMD 检测
    result = _detect_pmd(sample)
    if result:
        result.encoding = encoding
        result.sample_lines = sample
        result.total_lines = len(lines)
        return result

    # 2. DIR 检测
    result = _detect_dir(sample)
    if result:
        result.encoding = encoding
        result.sample_lines = sample
        result.total_lines = len(lines)
        return result

    # 3. 表格检测（分隔符推断）
    sep, score = _detect_separator(sample)
    result = _detect_tabular(sample, sep, score)
    if result:
        result.encoding = encoding
        result.sample_lines = sample
        result.total_lines = len(lines)
        return result

    # 4. 通用文本兜底
    header_row, data_start, preamble, header_cols = _detect_header_and_preamble(sample, " ")
    return DetectResult(
        format_type="generic_text",
        confidence=0.3,
        encoding=encoding,
        separator=" ",
        header_row=header_row,
        data_start_row=data_start,
        preamble_lines=preamble,
        header_columns=header_cols,
        parser_name="generic_text",
        sample_lines=sample,
        total_lines=len(lines),
    )
