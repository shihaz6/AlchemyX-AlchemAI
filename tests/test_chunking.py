import pytest

from alchemyx.retrieval.chunking import chunk_text


def test_empty_text():
    assert chunk_text("") == []


def test_overlap_and_coverage():
    text = "one two three four five six seven eight"
    assert chunk_text(text, chunk_size=4, overlap=1, min_chunk_size=0) == [
        "one two three four", "four five six seven", "seven eight"
    ]


@pytest.mark.parametrize("kwargs", [
    {"chunk_size": 0}, {"overlap": -1},
    {"chunk_size": 4, "overlap": 4}, {"min_chunk_size": -1},
])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        chunk_text("sample", **kwargs)
