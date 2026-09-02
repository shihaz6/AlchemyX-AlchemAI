from src.alchemyx.agent.schemas import ConflictResult, SufficiencyResult
from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult
from src.alchemyx import backend_adapter


class FakeSystem:

    def ask(self, question):
        return {
            "answer": "Santiago is a shepherd. [book.pdf_chunk12]",
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
            "timeline": [
                {
                    "iteration": 1,
                    "query": question,
                    "retrieved": 3,
                    "reranked": 1,
                    "distinct_sources": 1,
                    "new_evidence": 1,
                    "new_evidence_summary": "New evidence from book.pdf.",
                    "conflict_detected": False,
                    "conflict_resolved": False,
                    "candidate_values": [],
                    "missing": [],
                    "next_queries": [],
                    "sufficient": True,
                    "stop_reason": "sufficient_evidence",
                    "elapsed_seconds": 0.4,
                }
            ],
            "timings": {
                "agent_loop": 1.2,
                "final_generation": 0.8,
                "end_to_end": 2.0,
            },
        }


def test_run_research_maps_system_result_to_streamlit_contract(monkeypatch):
    monkeypatch.setattr(backend_adapter, "get_system", lambda: FakeSystem())

    result = backend_adapter.run_research("Who is Santiago?")

    assert result["answer"] == "Santiago is a shepherd. [book.pdf_chunk12]"
    assert result["clean_answer"] == "Santiago is a shepherd. [Book]"
    assert result["iterations"] == 1
    assert result["sufficient"] is True
    assert result["sources_retrieved"] == 1
    assert result["chunks_retrieved"] == 1
    assert result["conflict"]["status"] == "None"
    assert result["steps"][0]["title"] == "Hybrid Retrieval"
    assert result["sources"] == [
        {
            "source_family_id": "book",
            "title": "Book",
            "document_type": "PDF",
            "formats": ["PDF"],
            "claim": "",
            "role": "supporting",
            "authority_assessment": "Available evidence",
            "authority_summary": "",
            "reason": "",
            "chunk_ids": ["book.pdf_chunk12"],
            "chunks": 1,
            "chunk_numbers": [12],
            "excerpt": "Santiago was a shepherd.",
            "technical_details": [
                {
                    "id": "book.pdf_chunk12",
                    "source_doc": "book.pdf",
                    "chunk_index": 12,
                    "score": 0.87,
                }
            ],
        }
    ]
    assert result["timeline"][0]["iteration"] == 1
    assert result["timeline"][0]["conflict_status"] == "None"
    assert result["timings"]["end_to_end"] == 2.0
    assert result["technical_sources"][0]["id"] == "book.pdf_chunk12"


def test_backend_groups_duplicate_formats_as_one_source_family(monkeypatch):
    class DuplicateSystem:
        def ask(self, question):
            return {
                "answer": "The value is 12. [archive_k.pdf_chunk1, archive_k.docx_chunk1]",
                "documents": [
                    RetrievalResult("archive_k.pdf_chunk1", "Archive K says the value is 12.", "archive_k.pdf", 1, 0.9),
                    RetrievalResult("archive_k.docx_chunk1", "Archive K says the value is 12.", "archive_k.docx", 1, 0.8),
                ],
                "citations": [],
                "sufficiency_result": SufficiencyResult(
                    sufficient=True,
                    missing=[],
                    search_queries=[],
                    evidence_ids=["archive_k.pdf_chunk1"],
                    reason="Evidence answers the question.",
                ),
                "iterations": 1,
                "stop_reason": "sufficient_evidence",
                "timeline": [],
                "timings": {"agent_loop": 1.0, "final_generation": 2.0, "end_to_end": 3.0},
            }

    monkeypatch.setattr(backend_adapter, "get_system", lambda: DuplicateSystem())

    result = backend_adapter.run_research("What is the value?")

    assert result["sources_retrieved"] == 1
    assert result["sources"][0]["formats"] == ["DOCX", "PDF"]
    assert result["sources"][0]["chunks"] == 2
    assert result["technical_sources"][0]["id"] == "archive_k.pdf_chunk1"
    assert result["technical_sources"][1]["id"] == "archive_k.docx_chunk1"


def test_backend_resolved_conflict_summary_is_ui_ready(monkeypatch):
    class ConflictSystem:
        def ask(self, question):
            conflict = ConflictResult(
                has_conflict=True,
                claim="Metric T value",
                candidate_values=["100", "104"],
                supporting_evidence_ids={
                    "100": ["popular_chunk0"],
                    "104": ["record_chunk0"],
                },
                authority_notes=["The selected record directly corrects the popular account."],
                recommended_search_queries=[],
                resolvable=True,
                resolved=True,
                selected_value="104",
                selected_evidence_ids=["record_chunk0"],
                reason="The record explicitly resolves the disagreement.",
            )
            return {
                "answer": "104 is best supported. [record_chunk0]",
                "documents": [
                    RetrievalResult("popular_chunk0", "A popular account says Metric T is 100.", "popular.txt", 0, 0.7),
                    RetrievalResult("record_chunk0", "The official record says Metric T is 104, not 100.", "record.txt", 0, 0.95),
                ],
                "citations": [],
                "sufficiency_result": SufficiencyResult(
                    sufficient=True,
                    missing=[],
                    search_queries=[],
                    evidence_ids=["record_chunk0"],
                    reason="Resolved.",
                    conflict_result=conflict,
                ),
                "iterations": 2,
                "stop_reason": "sufficient_evidence",
                "timeline": [
                    {"iteration": 1, "query": question, "sufficient": False, "conflict_detected": True, "candidate_values": ["100", "104"]},
                    {"iteration": 2, "query": "official Metric T record", "sufficient": True, "conflict_detected": True, "conflict_resolved": True, "candidate_values": ["100", "104"]},
                ],
                "timings": {"agent_loop": 4.0, "final_generation": 2.5, "end_to_end": 6.5},
            }

    monkeypatch.setattr(backend_adapter, "get_system", lambda: ConflictSystem())

    result = backend_adapter.run_research("What is the actual Metric T value?")

    assert result["conflict"]["status"] == "Resolved"
    assert result["conflict"]["candidate_values"] == ["100", "104"]
    assert result["conflict"]["selected_value"] == "104"
    assert "explicitly resolves" in result["conflict"]["resolution_summary"]
    assert [item["iteration"] for item in result["timeline"]] == [1, 2]
    assert result["timeline"][1]["conflict_status"] == "Resolved"


def test_backend_unresolved_conflict_status(monkeypatch):
    class ConflictSystem:
        def ask(self, question):
            conflict = ConflictResult(
                has_conflict=True,
                claim="Metric U value",
                candidate_values=["red", "blue"],
                supporting_evidence_ids={"red": ["left_chunk0"], "blue": ["right_chunk0"]},
                resolvable=False,
                resolved=False,
                reason="No higher-authority source was retrieved.",
            )
            return {
                "answer": "The evidence remains unresolved.",
                "documents": [
                    RetrievalResult("left_chunk0", "Record Left says red.", "left.txt", 0, 0.8),
                    RetrievalResult("right_chunk0", "Record Right says blue.", "right.txt", 0, 0.8),
                ],
                "citations": [],
                "sufficiency_result": SufficiencyResult(
                    sufficient=False,
                    missing=["Metric U value"],
                    search_queries=[],
                    evidence_ids=["left_chunk0", "right_chunk0"],
                    reason="Unresolved.",
                    conflict_result=conflict,
                ),
                "iterations": 2,
                "stop_reason": "no_search_query",
                "timeline": [],
                "timings": {"agent_loop": 1.0, "final_generation": 1.0, "end_to_end": 2.0},
            }

    monkeypatch.setattr(backend_adapter, "get_system", lambda: ConflictSystem())

    result = backend_adapter.run_research("What is the actual Metric U value?")

    assert result["conflict"]["status"] == "Unresolved"
    assert result["sufficient"] is False


def test_backend_generates_readable_source_labels():
    assert (
        backend_adapter.readable_source_label("folder/source_alpha_ii.scan.pdf")
        == "Source Alpha II"
    )
