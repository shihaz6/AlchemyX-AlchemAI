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


def test_prose_chunking_prefers_sentence_boundaries():
    chunks = chunk_text(
        "First sentence is here. Second sentence stays intact. "
        "Third sentence starts a new chunk.",
        chunk_size=7,
        overlap=0,
        min_chunk_size=1,
    )

    assert chunks == [
        "First sentence is here.",
        "Second sentence stays intact.",
        "Third sentence starts a new chunk.",
    ]


def test_long_sentence_falls_back_to_word_window():
    chunks = chunk_text(
        "one two three four five six seven eight.",
        chunk_size=4,
        overlap=1,
        min_chunk_size=1,
    )

    assert chunks == [
        "one two three four",
        "four five six seven",
        "seven eight.",
    ]


def test_tiny_trailing_chunk_merges_into_previous_chunk():
    assert chunk_text(
        "one two three four five six",
        chunk_size=5,
        overlap=1,
        min_chunk_size=3,
    ) == ["one two three four five six"]


def test_markdown_chunks_preserve_heading_sections_without_cross_section_overlap():
    text = (
        "# Title\n\n"
        "Opening context for the page.\n\n"
        "## Background\n\n"
        "Background sentence one. Background sentence two.\n\n"
        "## Aftermath\n\n"
        "Aftermath sentence one. Aftermath sentence two."
    )

    chunks = chunk_text(
        text,
        chunk_size=20,
        overlap=5,
        document_type="md",
    )

    assert chunks == [
        "# Title Opening context for the page.",
        "## Background Background sentence one. Background sentence two.",
        "## Aftermath Aftermath sentence one. Aftermath sentence two.",
    ]


def test_long_markdown_section_repeats_heading_without_gluing_next_heading():
    chunks = chunk_text(
        "## Long Section\n\none two three four five six seven eight nine ten",
        chunk_size=7,
        overlap=2,
        min_chunk_size=1,
        document_type="md",
    )

    assert chunks == [
        "## Long Section one two three four",
        "## Long Section three four five six",
        "## Long Section five six seven eight",
        "## Long Section seven eight nine ten",
    ]
