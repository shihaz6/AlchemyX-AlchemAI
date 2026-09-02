from src.alchemyx.agent.schemas import SufficiencyResult
from src.alchemyx.generation.answer_generator import (
    AnswerGenerator,
    GeneratedAnswer,
    build_answer_prompt,
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
        return "Caldrin escorted Mira Quen. [caldrin_wiki_chunk2]"


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


def test_build_answer_prompt_mentions_incomplete_evidence_instruction():
    prompt = build_answer_prompt("Question?", [], None)

    assert "If the evidence is" in prompt
    assert "incomplete" in prompt
    assert "Do not invent facts" in prompt


def test_answer_generator_does_not_call_llm_without_evidence():
    llm_client = FakeLLMClient()

    result = AnswerGenerator(llm_client).generate(
        question="Question?",
        documents=[],
    )

    assert result.evidence_ids == []
    assert "could not find sufficient evidence" in result.answer
    assert llm_client.prompts == []


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
