"""Detect structural features in text chunks (tables, lists, code, specs)."""

import re
from typing import Dict, List, Tuple

# Table patterns: pipe-delimited, ASCII tables, aligned columns
_TABLE_PATTERNS = [
    re.compile(r'\|.*\|.*\|', re.MULTILINE),           # pipe-delimited tables
    re.compile(r'[\+\-]{3,}[\+\-]+', re.MULTILINE),    # ASCII table borders (+---+---+)
    re.compile(r'^\s*\S+\s{2,}\S+\s{2,}\S+', re.MULTILINE),  # aligned columns (3+ cols)
]

# List patterns: bullets, numbered items, lettered items
_LIST_PATTERNS = [
    re.compile(r'^\s*[-•*]\s+\S', re.MULTILINE),       # bullet lists
    re.compile(r'^\s*\d{1,3}[.)]\s+\S', re.MULTILINE), # numbered lists
    re.compile(r'^\s*[a-zA-Z][.)]\s+\S', re.MULTILINE), # lettered lists
]

# Specification patterns: key-value pairs, model numbers, dimensions
_SPEC_PATTERNS = [
    re.compile(r'[\w\s]+:\s+\d[\d.,]*\s*\w*', re.MULTILINE),  # key: value pairs
    re.compile(r'[A-Z]{2,}[\-/]\d{2,}'),                       # model numbers (FX5U-32MR)
    re.compile(r'\d+\s*[×xX]\s*\d+'),                          # dimensions (100 x 50)
    re.compile(r'[±]\s*\d'),                                     # tolerances (±5%)
]

# Section header patterns
_HEADER_PATTERNS = [
    re.compile(r'^(Section|Article|Chapter|Part|Clause|Appendix)\s+\d', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^\d+\.\d*\s+[A-Z]', re.MULTILINE),          # "1.2 Title" numbered headings
    re.compile(r'^[A-Z][A-Z\s]{4,}$', re.MULTILINE),          # ALL-CAPS lines (min 5 chars)
    re.compile(r'^#{1,4}\s+\S', re.MULTILINE),                 # Markdown headings
]


def detect_structure(text: str) -> Dict[str, any]:
    """Detect structural features of a text chunk.

    Returns dict with:
        has_table: bool
        has_list: bool
        has_specs: bool
        structure_type: str - primary structure type
        list_item_count: int - number of list items detected
        table_row_count: int - number of table rows detected
    """
    lines = text.split('\n')
    line_count = len(lines)

    # Table detection
    table_matches = sum(
        1 for p in _TABLE_PATTERNS
        for _ in p.finditer(text)
    )
    has_table = table_matches >= 2  # need at least 2 matches to be a real table

    # List detection
    list_items = sum(
        len(p.findall(text)) for p in _LIST_PATTERNS
    )
    has_list = list_items >= 3  # need at least 3 items

    # Spec detection
    spec_matches = sum(
        len(p.findall(text)) for p in _SPEC_PATTERNS
    )
    has_specs = spec_matches >= 2

    # Classify primary structure type
    if has_table:
        structure_type = "table"
    elif has_list and list_items > 5:
        structure_type = "list"
    elif has_specs and spec_matches > 3:
        structure_type = "specification"
    elif has_list:
        structure_type = "mixed"
    else:
        structure_type = "prose"

    return {
        "has_table": has_table,
        "has_list": has_list,
        "has_specs": has_specs,
        "structure_type": structure_type,
        "list_item_count": list_items,
        "table_row_count": table_matches,
    }


def find_headers(text: str) -> List[Tuple[int, str]]:
    """Find section headers in text.

    Returns list of (char_offset, header_text) tuples, sorted by offset.
    """
    headers = []
    for pattern in _HEADER_PATTERNS:
        for m in pattern.finditer(text):
            header_text = m.group().strip()
            # Skip very short ALL-CAPS matches that are likely abbreviations
            if len(header_text) < 5:
                continue
            headers.append((m.start(), header_text))
    headers.sort(key=lambda x: x[0])
    return headers


def detect_blocks(text: str) -> List[Tuple[int, int, str]]:
    """Detect structural blocks in text for structure-aware chunking.

    Scans the full text and identifies contiguous regions that form structural
    units (tables, lists, spec blocks). These blocks should not be split during
    chunking.

    Returns:
        List of (start_idx, end_idx, block_type) tuples.
        block_type is one of: "table", "list", "specification", "header"
        Spans may not cover the entire text — gaps are prose.
    """
    blocks = []
    lines = text.split('\n')
    if not lines:
        return blocks

    # Build line offset map: line_index -> char offset of line start
    line_offsets = []
    offset = 0
    for line in lines:
        line_offsets.append(offset)
        offset += len(line) + 1  # +1 for \n

    def _line_end(idx: int) -> int:
        """Char offset of end of line idx."""
        return line_offsets[idx] + len(lines[idx])

    # Detect table blocks: consecutive lines with table patterns
    table_re = re.compile(r'\|.*\|.*\||[\+\-]{3,}[\+\-]+|^\s*\S+\s{2,}\S+\s{2,}\S+', re.MULTILINE)
    in_table = False
    table_start = None
    for i, line in enumerate(lines):
        is_table_line = bool(table_re.search(line))
        if is_table_line and not in_table:
            in_table = True
            table_start = i
        elif not is_table_line and in_table:
            # End of table block — require at least 2 lines
            if i - table_start >= 2:
                blocks.append((line_offsets[table_start], _line_end(i - 1), "table"))
            in_table = False
    if in_table and table_start is not None and len(lines) - table_start >= 2:
        blocks.append((line_offsets[table_start], _line_end(len(lines) - 1), "table"))

    # Detect list blocks: consecutive list items
    list_re = re.compile(r'^\s*(?:[-•*]\s+\S|\d{1,3}[.)]\s+\S|[a-zA-Z][.)]\s+\S)')
    in_list = False
    list_start = None
    for i, line in enumerate(lines):
        is_list_line = bool(list_re.match(line))
        # Also count continuation lines (indented non-empty lines following a list item)
        is_continuation = in_list and line.strip() and line.startswith('  ') and not is_list_line
        if (is_list_line or is_continuation) and not in_list:
            if is_list_line:
                in_list = True
                list_start = i
        elif is_list_line or is_continuation:
            pass  # still in list
        elif in_list:
            if i - list_start >= 3:
                blocks.append((line_offsets[list_start], _line_end(i - 1), "list"))
            in_list = False
    if in_list and list_start is not None and len(lines) - list_start >= 3:
        blocks.append((line_offsets[list_start], _line_end(len(lines) - 1), "list"))

    # Detect header lines
    for pattern in _HEADER_PATTERNS:
        for m in pattern.finditer(text):
            header_text = m.group().strip()
            if len(header_text) >= 5:
                blocks.append((m.start(), m.end(), "header"))

    # Sort by start offset; remove overlapping blocks (keep larger)
    blocks.sort(key=lambda b: (b[0], -(b[1] - b[0])))
    merged = []
    for block in blocks:
        if merged and block[0] < merged[-1][1]:
            # Overlapping — keep the larger one
            if (block[1] - block[0]) > (merged[-1][1] - merged[-1][0]):
                merged[-1] = block
        else:
            merged.append(block)

    return merged
