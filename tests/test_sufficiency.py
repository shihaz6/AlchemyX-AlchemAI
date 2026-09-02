import json

from src.alchemyx.agent.sufficiency_checker import SufficiencyChecker
from src.alchemyx.agent.prompts import build_sufficiency_prompt
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


def test_sufficiency_prompt_preserves_question_and_does_not_expand_task():
    prompt = build_sufficiency_prompt("who is the author of the book", [])

    assert "ORIGINAL QUESTION:\nwho is the author of the book" in prompt
    assert "immutable" in prompt
    assert "Do not replace \"the book\" with a title" in prompt
    assert "plot, themes, motivation" in prompt


def test_sufficiency_prompt_treats_supported_uncertainty_as_sufficient():
    prompt = build_sufficiency_prompt(
        "What happened to Caldrin after the Night of Falling Bells",
        [],
    )

    assert "unknown, unconfirmed, disputed, or not recorded" in prompt
    assert "uncertainty answer" in prompt


def test_sufficiency_checker_accepts_markdown_fenced_json():
    class FencedLLM:
        def ask(self, prompt):
            return '''```json
{"sufficient": true, "missing": [], "search_queries": [],
 "evidence_ids": ["doc_1"], "reason": "Evidence answers the question."}
```'''

    documents = [
        RetrievalResult(
            id="doc_1",
            text="The evidence answers the question.",
            source_doc="fake",
            chunk_index=0,
            score=1.0,
        )
    ]

    result = SufficiencyChecker(FencedLLM()).check("Who wrote this book?", documents)

    assert result.sufficient is True
    assert result.evidence_ids == ["doc_1"]


def test_sufficiency_checker_rejects_unretrieved_evidence_ids():
    class InvalidCitationLLM:
        def ask(self, prompt):
            return json.dumps(
                {
                    "sufficient": True,
                    "missing": [],
                    "search_queries": [],
                    "evidence_ids": ["mira_wiki_chunk0"],
                    "reason": "Evidence answers the question.",
                }
            )

    documents = [
        RetrievalResult(
            id="smugglers/mira_quen.txt_chunk0",
            text="Mira carried a reliquary.",
            source_doc="smugglers/mira_quen.txt",
            chunk_index=0,
            score=1.0,
        )
    ]

    try:
        SufficiencyChecker(InvalidCitationLLM()).check("What did Mira carry?", documents)
    except ValueError as exc:
        assert "not retrieved" in str(exc)
    else:
        raise AssertionError("Expected unretrieved evidence ID to be rejected")
