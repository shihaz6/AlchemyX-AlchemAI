import json

from src.alchemyx.agent.evidence_adjudicator import (
    EvidenceAdjudicator,
    distinct_source_family_count,
    parse_adjudication_response,
    source_family_id,
)
from src.alchemyx.agent.schemas import SufficiencyResult
from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult


def test_duplicate_pdf_docx_source_family_is_not_independent():
    documents = [
        RetrievalResult("doc_pdf_chunk0", "Archive K says value A.", "archive_k.pdf", 0, 1.0),
        RetrievalResult("doc_docx_chunk0", "Archive K says value A.", "archive_k.docx", 0, 1.0),
        RetrievalResult("other_chunk0", "Ledger M says value A.", "ledger_m.txt", 0, 1.0),
    ]

    assert source_family_id("folder/archive_k.pdf") == source_family_id("folder/archive_k.docx")
    assert source_family_id("folder/archive_k.scan.pdf") == source_family_id("folder/archive_k.pdf")
    assert distinct_source_family_count(documents) == 2


def test_adjudicator_detects_authority_sensitive_conflict_from_signals():
    documents = [
        RetrievalResult("alpha_chunk0", "Report Alpha says Metric T is 100.", "alpha.txt", 0, 1.0),
        RetrievalResult("beta_chunk0", "Report Beta disputes that and says Metric T is 104.", "beta.txt", 0, 1.0),
    ]
    result = SufficiencyResult(
        sufficient=True,
        missing=[],
        search_queries=[],
        evidence_ids=["alpha_chunk0"],
        reason="Relevant evidence exists.",
    )

    adjudicator = EvidenceAdjudicator(llm_client=None)

    assert adjudicator.should_adjudicate(
        "What is the exact Metric T value?",
        documents,
        result,
    )


def test_adjudicator_parses_structured_conflict_result():
    class LLM:
        def ask(self, prompt):
            assert "SOURCE FAMILY" in prompt
            return json.dumps(
                {
                    "has_conflict": True,
                    "claim": "Metric T value",
                    "candidate_values": ["100", "104"],
                    "supporting_evidence_ids": {
                        "100": ["alpha_chunk0"],
                        "104": ["beta_chunk0"],
                    },
                    "authority_notes": ["Beta directly corrects Alpha."],
                    "recommended_search_queries": ["official Metric T record"],
                    "resolvable": True,
                    "resolved": False,
                    "selected_value": "",
                    "selected_evidence_ids": [],
                    "reason": "Need the official record.",
                }
            )

    documents = [
        RetrievalResult("alpha_chunk0", "Report Alpha says Metric T is 100.", "alpha.txt", 0, 1.0),
        RetrievalResult("beta_chunk0", "Report Beta says Metric T is 104.", "beta.txt", 0, 1.0),
    ]

    result = EvidenceAdjudicator(LLM()).adjudicate("What is Metric T?", documents)

    assert result.has_conflict is True
    assert result.candidate_values == ["100", "104"]
    assert result.recommended_search_queries == ["official Metric T record"]


def parser_documents():
    return [
        RetrievalResult("alpha_chunk0", "Alpha states one value.", "alpha.txt", 0, 1.0),
        RetrievalResult("beta_chunk0", "Beta states another value.", "beta.txt", 0, 1.0),
    ]


def conflict_payload(**overrides):
    payload = {
        "has_conflict": True,
        "claim": "Metric value",
        "candidate_values": ["one", "two"],
        "supporting_evidence_ids": {"one": ["alpha_chunk0"]},
        "authority_notes": ["Alpha is direct."],
        "recommended_search_queries": ["official Metric value record"],
        "resolvable": True,
        "resolved": False,
        "selected_value": "",
        "selected_evidence_ids": [],
        "reason": "Needs follow-up.",
    }
    payload.update(overrides)
    return payload


def parse_payload(payload):
    return parse_adjudication_response(json.dumps(payload), parser_documents())


def test_parse_adjudication_response_accepts_correct_supporting_list():
    result = parse_payload(
        conflict_payload(
            supporting_evidence_ids={"one": ["alpha_chunk0", "beta_chunk0"]},
        )
    )

    assert result.supporting_evidence_ids == {
        "one": ["alpha_chunk0", "beta_chunk0"]
    }


def test_parse_adjudication_response_normalizes_supporting_string():
    result = parse_payload(
        conflict_payload(supporting_evidence_ids={"one": "alpha_chunk0"})
    )

    assert result.supporting_evidence_ids == {"one": ["alpha_chunk0"]}


def test_parse_adjudication_response_normalizes_supporting_null():
    result = parse_payload(conflict_payload(supporting_evidence_ids={"one": None}))

    assert result.supporting_evidence_ids == {"one": []}


def test_parse_adjudication_response_ignores_supporting_object_value():
    result = parse_payload(
        conflict_payload(supporting_evidence_ids={"one": {"id": "alpha_chunk0"}})
    )

    assert result.supporting_evidence_ids == {"one": []}


def test_parse_adjudication_response_discards_unknown_evidence_ids():
    result = parse_payload(
        conflict_payload(
            supporting_evidence_ids={"one": ["alpha_chunk0", "missing_chunk0"]},
            selected_evidence_ids=["missing_chunk0", "beta_chunk0"],
        )
    )

    assert result.supporting_evidence_ids == {"one": ["alpha_chunk0"]}
    assert result.selected_evidence_ids == ["beta_chunk0"]


def test_parse_adjudication_response_missing_supporting_evidence_ids_defaults_empty():
    payload = conflict_payload()
    payload.pop("supporting_evidence_ids")

    result = parse_payload(payload)

    assert result.supporting_evidence_ids == {}
    assert result.has_conflict is True


def test_parse_adjudication_response_malformed_payload_returns_safe_fallback():
    result = parse_adjudication_response("not-json", parser_documents())

    assert result.has_conflict is False
    assert result.supporting_evidence_ids == {}
    assert "invalid JSON" in result.reason
