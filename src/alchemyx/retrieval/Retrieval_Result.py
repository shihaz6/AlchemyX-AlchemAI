from dataclasses import dataclass


@dataclass
class RetrievalResult:
    id: str
    text: str
    source_doc: str
    chunk_index: int
    score: float