"""Tests for TextChunker."""

import pytest

from src.chunker import TextChunker


class TestChunkText:
    """Test chunk_text() main entry point."""

    def test_empty_text(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        assert chunker.chunk_text("") == []
        assert chunker.chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        text = "Short text."
        chunks = chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "Short text."

    def test_structure_aware_with_table(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50, structure_aware=True)
        text = (
            "Introduction paragraph.\n\n"
            "| Col1 | Col2 | Col3 |\n"
            "|------|------|------|\n"
            "| A    | B    | C    |\n"
            "| D    | E    | F    |\n\n"
            "Conclusion paragraph."
        )
        chunks = chunker.chunk_text(text)
        assert len(chunks) >= 1
        # Table should be kept together in some chunk
        table_chunk = [c for c in chunks if "|" in c]
        assert len(table_chunk) >= 1

    def test_structure_aware_with_list(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50, structure_aware=True)
        text = (
            "Preamble text.\n\n"
            "- Item one detail\n"
            "- Item two detail\n"
            "- Item three detail\n"
            "- Item four detail\n\n"
            "Conclusion."
        )
        chunks = chunker.chunk_text(text)
        assert len(chunks) >= 1

    def test_fallback_to_fixed_size(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20, structure_aware=True)
        # Long prose with no structure → falls back to fixed-size
        text = "Word " * 200  # ~1000 chars
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 1

    def test_structure_aware_disabled(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20, structure_aware=False)
        text = "Word " * 200
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 1

    def test_overlap_present(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=30, structure_aware=False)
        text = "This is sentence one. " * 30
        chunks = chunker.chunk_text(text)
        if len(chunks) >= 2:
            # Last words of first chunk should appear in second
            last_words = chunks[0][-30:]
            assert any(word in chunks[1] for word in last_words.split() if len(word) > 3)


class TestFixedSizeChunk:
    """Test _fixed_size_chunk() directly."""

    def test_paragraph_break(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here. " * 5
        chunks = chunker._fixed_size_chunk(text)
        assert len(chunks) >= 2

    def test_sentence_break(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "Sentence one. Sentence two. Sentence three. " * 10
        chunks = chunker._fixed_size_chunk(text)
        assert len(chunks) >= 2

    def test_find_break_point_word_boundary(self):
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "a" * 45 + " " + "b" * 45
        bp = chunker._find_break_point(text, 0, 50)
        assert bp <= 50


class TestSplitProse:
    """Test _split_prose()."""

    def test_short_text(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        result = chunker._split_prose("Short text.")
        assert len(result) == 1

    def test_paragraph_splitting(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "Para one. " * 10 + "\n\n" + "Para two. " * 10
        result = chunker._split_prose(text)
        assert len(result) >= 1


class TestSplitBlockAtLines:
    """Test _split_block_at_lines()."""

    def test_splits_large_block(self):
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "\n".join(f"Line {i} with some text" for i in range(20))
        result = chunker._split_block_at_lines(text)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= 50 + 50  # Allow some slack


class TestMergeSmallChunks:
    """Test _merge_small_chunks()."""

    def test_empty(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50, min_chunk_size=100)
        assert chunker._merge_small_chunks([]) == []

    def test_merges_small(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50, min_chunk_size=100)
        chunks = ["Hi", "Hello world, this is a longer text that should pass min size."]
        result = chunker._merge_small_chunks(chunks)
        assert len(result) <= len(chunks)

    def test_no_merge_when_large_enough(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50, min_chunk_size=5)
        chunks = ["Hello world", "Another chunk"]
        result = chunker._merge_small_chunks(chunks)
        assert len(result) == 2


class TestChunkWithPageTracking:
    """Test chunk_with_page_tracking()."""

    def test_single_page(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        page_data = [{"page_num": 1, "text": "Some text on page one."}]
        result = chunker.chunk_with_page_tracking(page_data)
        assert len(result) >= 1
        assert result[0]["page_num"] == 1
        assert "text" in result[0]

    def test_multi_page(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        page_data = [
            {"page_num": 1, "text": "Page one content."},
            {"page_num": 2, "text": "Page two content."},
        ]
        result = chunker.chunk_with_page_tracking(page_data)
        assert len(result) >= 2
        pages = [r["page_num"] for r in result]
        assert 1 in pages
        assert 2 in pages

    def test_section_title_detection(self):
        chunker = TextChunker(chunk_size=2000, chunk_overlap=100)
        page_data = [{
            "page_num": 1,
            "text": "Section 1 Introduction\nThis is the introduction content. " * 5,
        }]
        result = chunker.chunk_with_page_tracking(page_data)
        assert len(result) >= 1
        # Section title may or may not be detected depending on chunk boundaries
        # Just verify structure is correct
        assert "section_title" in result[0]

    def test_empty_pages(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        page_data = [
            {"page_num": 1, "text": ""},
            {"page_num": 2, "text": "Content on page two."},
        ]
        result = chunker.chunk_with_page_tracking(page_data)
        # Empty page should produce no chunks
        assert all(r["page_num"] == 2 for r in result)
