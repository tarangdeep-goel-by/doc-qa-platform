"""Detect structural features in text chunks (tables, lists, code, specs)."""

import re
from typing import Dict


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
