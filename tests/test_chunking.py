import pytest

from src.alchemyx.retrieval.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_short_document_returns_single_chunk():
    assert chunk_text("short document", chunk_size=10, overlap=0) == [
        "short document"
    ]


def test_overlap_equal_to_chunk_size_raises():
    with pytest.raises(ValueError, match="overlap must be smaller"):
        chunk_text("one two", chunk_size=2, overlap=2)


def test_overlap_greater_than_chunk_size_raises():
    with pytest.raises(ValueError, match="overlap must be smaller"):
        chunk_text("one two", chunk_size=2, overlap=3)


def test_normal_chunking_uses_overlap():
    assert chunk_text(
        "one two three four five six seven",
        chunk_size=4,
        overlap=1,
        min_chunk_size=1,
    ) == [
        "one two three four",
        "four five six seven",
    ]


def test_tiny_trailing_chunk_merges_into_previous_chunk():
    assert chunk_text(
        "one two three four five six",
        chunk_size=5,
        overlap=1,
        min_chunk_size=3,
    ) == ["one two three four five six"]
