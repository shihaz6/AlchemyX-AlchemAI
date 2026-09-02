from src.alchemyx.agent.schemas import SufficiencyResult
from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult
from src.alchemyx import backend_adapter


class FakeSystem:

    def ask(self, question):
        return {
            "answer": "Santiago is a shepherd.",
            "documents": [
                RetrievalResult(
                    id="book.pdf_chunk12",
                    text="Santiago was a shepherd.",
                    source_doc="book.pdf",
                    chunk_index=12,
                    score=0.87,
                )
            ],
            "citations": [
                {
                    "id": "book.pdf_chunk12",
                    "source": "book.pdf",
                    "chunk_index": 12,
                }
            ],
            "sufficiency_result": SufficiencyResult(
                sufficient=True,
                missing=[],
                search_queries=[],
                evidence_ids=["book.pdf_chunk12"],
                reason="Evidence identifies Santiago.",
            ),
            "iterations": 1,
            "stop_reason": "sufficient_evidence",
        }


def test_run_research_maps_system_result_to_streamlit_contract(monkeypatch):
    monkeypatch.setattr(backend_adapter, "get_system", lambda: FakeSystem())

    result = backend_adapter.run_research("Who is Santiago?")

    assert result["answer"] == "Santiago is a shepherd."
    assert result["iterations"] == 1
    assert result["sufficient"] is True
    assert result["sources_retrieved"] == 1
    assert result["steps"][0]["title"] == "Hybrid Retrieval"
    assert result["sources"] == [
        {
            "id": "book.pdf_chunk12",
            "title": "book.pdf",
            "source_doc": "book.pdf",
            "chunk_index": 12,
            "type": "Document",
            "text": "Santiago was a shepherd.",
            "excerpt": "Santiago was a shepherd.",
            "score": 0.87,
            "relevance": "0.87",
        }
    ]
