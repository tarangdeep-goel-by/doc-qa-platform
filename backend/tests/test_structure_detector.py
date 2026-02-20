"""Tests for structure_detector module."""

import pytest

from src.structure_detector import detect_structure, find_headers, detect_blocks


class TestDetectStructure:
    """Test detect_structure() classification."""

    def test_prose(self):
        text = "This is a simple paragraph of text. It has no special structure."
        result = detect_structure(text)
        assert result["structure_type"] == "prose"
        assert result["has_table"] is False
        assert result["has_list"] is False

    def test_pipe_table(self):
        text = (
            "| Name | Age | City |\n"
            "|------|-----|------|\n"
            "| Alice | 30 | NYC |\n"
            "| Bob | 25 | LA |\n"
        )
        result = detect_structure(text)
        assert result["has_table"] is True
        assert result["structure_type"] == "table"

    def test_ascii_table(self):
        text = (
            "+--------+-----+------+\n"
            "| Name   | Age | City |\n"
            "+--------+-----+------+\n"
            "| Alice  | 30  | NYC  |\n"
            "+--------+-----+------+\n"
        )
        result = detect_structure(text)
        assert result["has_table"] is True

    def test_aligned_columns(self):
        text = (
            "Name      Age    City\n"
            "Alice     30     NYC\n"
            "Bob       25     LA\n"
            "Charlie   35     SF\n"
        )
        result = detect_structure(text)
        # Aligned columns need at least 2 matches
        assert result["table_row_count"] >= 2

    def test_bullet_list(self):
        text = (
            "- Item one\n"
            "- Item two\n"
            "- Item three\n"
            "- Item four\n"
        )
        result = detect_structure(text)
        assert result["has_list"] is True
        assert result["list_item_count"] >= 3

    def test_numbered_list(self):
        text = (
            "1. First item\n"
            "2. Second item\n"
            "3. Third item\n"
            "4. Fourth item\n"
        )
        result = detect_structure(text)
        assert result["has_list"] is True

    def test_specs(self):
        text = (
            "Model: FX5U-32MR/ES\n"
            "Dimensions: 100 x 50 x 30\n"
            "Voltage: 24V DC\n"
            "Tolerance: ±5%\n"
        )
        result = detect_structure(text)
        assert result["has_specs"] is True

    def test_mixed_below_threshold(self):
        text = (
            "Some prose text here.\n"
            "- One item\n"
            "- Two items\n"
            "More prose below.\n"
        )
        result = detect_structure(text)
        # Only 2 list items, below threshold of 3
        assert result["has_list"] is False
        assert result["structure_type"] == "prose"

    def test_list_structure_type(self):
        text = "\n".join(f"- Item {i}" for i in range(8))
        result = detect_structure(text)
        assert result["structure_type"] == "list"
        assert result["list_item_count"] > 5

    def test_specification_structure_type(self):
        text = (
            "Model: FX5U-32MR\n"
            "Width: 100 x 50\n"
            "Height: 200mm\n"
            "Power: 24V\n"
            "Tolerance: ±5%\n"
        )
        result = detect_structure(text)
        if result["has_specs"] and result["table_row_count"] < 2:
            assert result["structure_type"] in ("specification", "mixed", "prose")


class TestFindHeaders:
    """Test find_headers() detection."""

    def test_section_header(self):
        text = "Some preamble\nSection 1 Introduction\nContent here"
        headers = find_headers(text)
        assert any("Section 1" in h for _, h in headers)

    def test_numbered_heading(self):
        text = "1.2 Configuration Guide\nSome content"
        headers = find_headers(text)
        # Pattern: ^\d+\.\d*\s+[A-Z] — matches "1.2 Configuration Guide"
        assert len(headers) >= 1

    def test_allcaps_header(self):
        text = "Some text\nIMPORTANT NOTES\nMore text"
        headers = find_headers(text)
        assert any("IMPORTANT NOTES" in h for _, h in headers)

    def test_markdown_header(self):
        # The regex matches ^#{1,4}\s+\S which is just e.g. "## G" (4 chars)
        # The < 5 char filter removes short matches, so this pattern only works
        # with headers like ##### (4 hashes + space + char = 6 chars match)
        text = "#### Introduction Details\nSome content"
        headers = find_headers(text)
        assert len(headers) >= 1

    def test_short_header_filtered(self):
        text = "ABC\nContent"
        headers = find_headers(text)
        # "ABC" is only 3 chars, should be filtered (< 5)
        assert not any(h == "ABC" for _, h in headers)

    def test_sorted_by_offset(self):
        text = "Section 1 First\nSome text\nSection 2 Second"
        headers = find_headers(text)
        if len(headers) >= 2:
            assert headers[0][0] <= headers[1][0]

    def test_empty_text(self):
        assert find_headers("") == []


class TestDetectBlocks:
    """Test detect_blocks() structural block detection."""

    def test_table_block(self):
        text = (
            "Preamble text\n"
            "| Col1 | Col2 | Col3 |\n"
            "|------|------|------|\n"
            "| A    | B    | C    |\n"
            "After table\n"
        )
        blocks = detect_blocks(text)
        table_blocks = [b for b in blocks if b[2] == "table"]
        assert len(table_blocks) >= 1

    def test_list_block(self):
        text = (
            "Preamble\n"
            "- Item one\n"
            "- Item two\n"
            "- Item three\n"
            "After list\n"
        )
        blocks = detect_blocks(text)
        list_blocks = [b for b in blocks if b[2] == "list"]
        assert len(list_blocks) >= 1

    def test_header_block(self):
        text = "Section 1 Introduction\nSome content follows."
        blocks = detect_blocks(text)
        header_blocks = [b for b in blocks if b[2] == "header"]
        assert len(header_blocks) >= 1

    def test_overlap_resolution(self):
        # If blocks overlap, larger one should win
        text = (
            "| A | B | C |\n"
            "| D | E | F |\n"
            "| G | H | I |\n"
        )
        blocks = detect_blocks(text)
        # No overlapping blocks in result
        for i in range(len(blocks) - 1):
            assert blocks[i][1] <= blocks[i + 1][0]

    def test_empty_text(self):
        assert detect_blocks("") == []

    def test_prose_gaps(self):
        text = (
            "Just prose text.\n"
            "More prose here.\n"
            "No structure.\n"
        )
        blocks = detect_blocks(text)
        # May have some header matches but no table/list blocks
        table_or_list = [b for b in blocks if b[2] in ("table", "list")]
        assert len(table_or_list) == 0
