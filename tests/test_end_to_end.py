from src.alchemyx.agent.schemas import SufficiencyResult
from src.alchemyx.generation.answer_generator import AnswerGenerator
from src.alchemyx.main import AlchemyXSystem
from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult

from scripts.evaluate import evaluate_questions, summarize


class FakeAgent:

    def __init__(self):
        self.documents = [
            RetrievalResult(
                id="caldrin_wiki_chunk2",
                text="Caldrin escorted Mira Quen.",
                source_doc="caldrin_wiki",
                chunk_index=2,
                score=0.9,
            )
        ]

    def run(self, question):
        return {
            "documents": self.documents,
            "result": SufficiencyResult(
                sufficient=True,
                missing=[],
                search_queries=[],
                evidence_ids=["caldrin_wiki_chunk2"],
                reason="Evidence is enough.",
            ),
            "iterations": 1,
            "stop_reason": "sufficient_evidence",
        }


class FakeLLMClient:

    def ask(self, prompt):
        return """{
            "answer": "Caldrin escorted Mira Quen. [caldrin_wiki_chunk2]",
            "evidence_ids": ["caldrin_wiki_chunk2"]
        }"""


def test_system_ask_returns_answer_citations_and_agent_metadata():
    system = AlchemyXSystem(
        agent=FakeAgent(),
        answer_generator=AnswerGenerator(FakeLLMClient()),
    )

    result = system.ask("Who did Caldrin escort?")

    assert result["answer"] == "Caldrin escorted Mira Quen. [caldrin_wiki_chunk2]"
    assert result["answer_evidence_ids"] == ["caldrin_wiki_chunk2"]
    assert result["citations"] == [
        {
            "id": "caldrin_wiki_chunk2",
            "source": "caldrin_wiki",
            "chunk_index": 2,
        }
    ]
    assert result["iterations"] == 1
    assert result["stop_reason"] == "sufficient_evidence"


def test_evaluator_records_metrics_from_system_results():
    system = AlchemyXSystem(
        agent=FakeAgent(),
        answer_generator=AnswerGenerator(FakeLLMClient()),
    )
    questions = [
        {
            "question": "Who did Caldrin escort?",
            "expected_source": "caldrin_wiki",
            "expected_sources": ["caldrin_wiki"],
            "expected_chunk": "caldrin_wiki_chunk2",
        }
    ]

    rows = evaluate_questions(system, questions)
    metrics = summarize(rows)

    assert rows[0]["retrieval_hit"] is True
    assert rows[0]["expected_chunk_rank"] == 1
    assert rows[0]["source_recall_at_5"] == 1.0
    assert rows[0]["iterations"] == 1
    assert rows[0]["sufficiency_reached"] is True
    assert rows[0]["answer_produced"] is True
    assert metrics["recall_at_5"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["average_iterations"] == 1.0
    assert metrics["success_rate"] == 1.0
