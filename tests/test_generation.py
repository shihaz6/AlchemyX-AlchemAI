from src.alchemyx.agent.schemas import ConflictResult, SufficiencyResult
from src.alchemyx.generation.answer_generator import (
    AnswerGenerator,
    GeneratedAnswer,
    build_answer_prompt,
    parse_answer_response,
    validate_citation_support,
)
from src.alchemyx.generation.citation_builder import (
    build_citations,
    format_citations,
)
from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult


class FakeLLMClient:

    def __init__(self):
        self.prompts = []

    def ask(self, prompt):
        self.prompts.append(prompt)
        return """{
            "answer": "Caldrin escorted Mira Quen. [caldrin_wiki_chunk2]",
            "evidence_ids": ["caldrin_wiki_chunk2"]
        }"""


def make_documents():
    return [
        RetrievalResult(
            id="caldrin_wiki_chunk2",
            text="Caldrin escorted Mira Quen to Thornwatch.",
            source_doc="caldrin_wiki",
            chunk_index=2,
            score=0.9,
        )
    ]


def test_answer_generator_uses_only_supplied_evidence_prompt():
    llm_client = FakeLLMClient()
    generator = AnswerGenerator(llm_client)
    documents = make_documents()

    result = generator.generate(
        question="Who did Caldrin escort?",
        documents=documents,
        sufficiency_result=SufficiencyResult(
            sufficient=True,
            missing=[],
            search_queries=[],
            evidence_ids=["caldrin_wiki_chunk2"],
            reason="Evidence identifies the escort target.",
        ),
    )

    assert isinstance(result, GeneratedAnswer)
    assert result.answer == "Caldrin escorted Mira Quen. [caldrin_wiki_chunk2]"
    assert result.evidence_ids == ["caldrin_wiki_chunk2"]
    assert "Use only the supplied evidence" in llm_client.prompts[0]
    assert "[EVIDENCE ID: caldrin_wiki_chunk2]" in llm_client.prompts[0]
    assert "ALLOWED EVIDENCE IDS:\ncaldrin_wiki_chunk2" in llm_client.prompts[0]


def test_build_answer_prompt_mentions_incomplete_evidence_instruction():
    prompt = build_answer_prompt("Question?", [], None)

    assert "If the evidence is" in prompt
    assert "incomplete" in prompt
    assert "Do not invent facts" in prompt


def test_build_answer_prompt_includes_resolved_conflict_guidance():
    prompt = build_answer_prompt(
        "What is the true Metric T value?",
        make_documents(),
        SufficiencyResult(
            sufficient=True,
            missing=[],
            search_queries=[],
            evidence_ids=["caldrin_wiki_chunk2"],
            reason="Resolved conflict.",
            conflict_result=ConflictResult(
                has_conflict=True,
                claim="Metric T value",
                candidate_values=["100", "104"],
                supporting_evidence_ids={"104": ["caldrin_wiki_chunk2"]},
                resolved=True,
                selected_value="104",
                selected_evidence_ids=["caldrin_wiki_chunk2"],
                reason="A correction source resolved the conflict.",
            ),
        ),
    )

    assert "CONFLICT ADJUDICATION" in prompt
    assert "selected_value: 104" in prompt
    assert "Do not say \"cannot be determined\"" in prompt


def test_answer_generator_does_not_call_llm_without_evidence():
    llm_client = FakeLLMClient()

    result = AnswerGenerator(llm_client).generate(
        question="Question?",
        documents=[],
    )

    assert result.evidence_ids == []
    assert "could not find sufficient evidence" in result.answer
    assert llm_client.prompts == []


def test_answer_generator_uses_sufficiency_evidence_ids_to_narrow_prompt():
    class NarrowingLLM:
        def __init__(self):
            self.prompt = ""

        def ask(self, prompt):
            self.prompt = prompt
            return """{
                "answer": "Mira carried a reliquary. [doc_chunk2]",
                "evidence_ids": ["doc_chunk2"]
            }"""

    documents = [
        RetrievalResult(
            id="doc_chunk1",
            text="Unrelated setup.",
            source_doc="doc",
            chunk_index=1,
            score=0.9,
        ),
        RetrievalResult(
            id="doc_chunk2",
            text="Mira carried a reliquary.",
            source_doc="doc",
            chunk_index=2,
            score=0.8,
        ),
    ]
    llm_client = NarrowingLLM()

    result = AnswerGenerator(llm_client).generate(
        question="What did Mira carry?",
        documents=documents,
        sufficiency_result=SufficiencyResult(
            sufficient=True,
            missing=[],
            search_queries=[],
            evidence_ids=["doc_chunk2"],
            reason="Evidence answers the question.",
        ),
    )

    assert result.evidence_ids == ["doc_chunk2"]
    assert "[EVIDENCE ID: doc_chunk2]" in llm_client.prompt
    assert "[EVIDENCE ID: doc_chunk1]" not in llm_client.prompt


def test_parse_answer_response_rejects_unsupplied_evidence_ids():
    documents = make_documents()

    try:
        parse_answer_response(
            """{
                "answer": "Mira is mentioned. [mira_wiki_chunk0]",
                "evidence_ids": ["mira_wiki_chunk0"]
            }""",
            documents,
        )
    except ValueError as exc:
        assert "not supplied" in str(exc)
    else:
        raise AssertionError("Expected unsupplied evidence ID to be rejected")


def test_validate_citation_support_rejects_valid_id_on_wrong_claim():
    documents = [
        RetrievalResult(
            id="doc_1_chunk0",
            text="Apple orchards grow beside the river.",
            source_doc="doc_1",
            chunk_index=0,
            score=0.9,
        ),
        RetrievalResult(
            id="doc_2_chunk0",
            text="Coolant failure affected Reactor Pump A.",
            source_doc="doc_2",
            chunk_index=0,
            score=0.8,
        ),
    ]

    try:
        validate_citation_support(
            "Coolant failure affected Reactor Pump A. [doc_1_chunk0]",
            documents,
        )
    except ValueError as exc:
        assert "weak lexical support" in str(exc)
    else:
        raise AssertionError("Expected weak citation support to be rejected")


def test_validate_citation_support_accepts_matching_claim_and_evidence():
    documents = [
        RetrievalResult(
            id="doc_2_chunk0",
            text="Coolant failure affected Reactor Pump A.",
            source_doc="doc_2",
            chunk_index=0,
            score=0.8,
        )
    ]

    validate_citation_support(
        "Coolant failure affected Reactor Pump A. [doc_2_chunk0]",
        documents,
    )


def test_build_and_format_citations():
    documents = make_documents() + make_documents()

    assert build_citations(documents) == [
        {
            "id": "caldrin_wiki_chunk2",
            "source": "caldrin_wiki",
            "chunk_index": 2,
        }
    ]
    assert format_citations(documents) == "[1] caldrin_wiki - chunk 2"
