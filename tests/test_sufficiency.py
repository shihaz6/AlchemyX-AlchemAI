import json

from src.alchemyx.agent.sufficiency_checker import SufficiencyChecker
from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult


class FakeLLMClient:

    def ask(self, prompt):
        assert "[EVIDENCE ID: doc_1]" in prompt
        assert "Component Y controls the coolant flow" in prompt

        return json.dumps(
            {
                "sufficient": False,
                "missing": ["identity of the escort"],
                "search_queries": ["Who did Caldrin escort?"],
                "evidence_ids": [],
                "reason": "Evidence does not identify the person.",
            }
        )


def test_sufficiency_checker_accepts_retrieval_results():
    documents = [
        RetrievalResult(
            id="doc_1",
            text="Component Y controls the coolant flow in Reactor Unit 4.",
            source_doc="fake",
            chunk_index=0,
            score=1.0,
        )
    ]

    checker = SufficiencyChecker(FakeLLMClient())

    result = checker.check(
        "Which equipment is affected when Component Y fails?",
        documents,
    )

    assert result.sufficient is False
    assert result.missing == ["identity of the escort"]
    assert result.search_queries == ["Who did Caldrin escort?"]
    assert result.evidence_ids == []
    assert result.reason == "Evidence does not identify the person."
