from src.alchemyx.agent.agent_loop import AgentLoop
from src.alchemyx.agent.schemas import SufficiencyResult
from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult
from tests.fake_retrieval import FakeRetrievalPipeline


class FakeSufficiencyChecker:

    def check(self, question, documents):
        if any(document.id == "doc_3" for document in documents):
            return SufficiencyResult(
                sufficient=True,
                missing=[],
                search_queries=[],
                evidence_ids=["doc_3"],
                reason="Found affected equipment.",
            )

        return SufficiencyResult(
            sufficient=False,
            missing=["affected equipment"],
            search_queries=["equipment affected by Component Y failure"],
            evidence_ids=["doc_1", "doc_2"],
            reason="Need affected equipment evidence.",
        )


class RepeatingSufficiencyChecker:

    def check(self, question, documents):
        return SufficiencyResult(
            sufficient=False,
            missing=["more evidence"],
            search_queries=[question],
            evidence_ids=[],
            reason="Repeated query.",
        )


class NoSearchQuerySufficiencyChecker:

    def check(self, question, documents):
        return SufficiencyResult(
            sufficient=False,
            missing=["more evidence"],
            search_queries=[],
            evidence_ids=[],
            reason="No actionable query.",
        )


class NeverSufficientChecker:

    def __init__(self):
        self.calls = 0

    def check(self, question, documents):
        self.calls += 1
        return SufficiencyResult(
            sufficient=False,
            missing=["more evidence"],
            search_queries=[f"followup {self.calls}"],
            evidence_ids=[],
            reason="Keep searching.",
        )


class EmptyRetrievalPipeline:

    def query(self, query):
        return []


class FailingSufficiencyChecker:

    def check(self, question, documents):
        raise AssertionError("Sufficiency should not run without evidence")


class CapturingChecker:
    def __init__(self):
        self.questions = []

    def check(self, question, documents):
        self.questions.append(question)
        return SufficiencyResult(
            sufficient=False,
            missing=["more evidence"],
            search_queries=["follow up"],
            evidence_ids=[],
            reason="Keep searching.",
        )


def test_agent_loop_accumulates_retrieval_results_until_sufficient():
    agent = AgentLoop(
        FakeRetrievalPipeline(),
        FakeSufficiencyChecker(),
    )

    result = agent.run("Which equipment is affected when Component Y fails?")

    assert result["stop_reason"] == "sufficient_evidence"
    assert result["iterations"] == 2
    assert [document.id for document in result["documents"]] == [
        "doc_1",
        "doc_2",
        "doc_3",
    ]


def test_agent_loop_stops_before_repeating_same_query():
    agent = AgentLoop(
        FakeRetrievalPipeline(),
        RepeatingSufficiencyChecker(),
    )

    result = agent.run("Which equipment is affected when Component Y fails?")

    assert result["stop_reason"] == "repeated_query"
    assert result["iterations"] == 1


def test_agent_loop_stops_when_no_search_query_is_available():
    agent = AgentLoop(
        FakeRetrievalPipeline(),
        NoSearchQuerySufficiencyChecker(),
    )

    result = agent.run("Which equipment is affected when Component Y fails?")

    assert result["stop_reason"] == "no_search_query"
    assert result["iterations"] == 1


def test_agent_loop_stops_at_max_iterations():
    agent = AgentLoop(
        FakeRetrievalPipeline(),
        NeverSufficientChecker(),
    )

    result = agent.run("Which equipment is affected when Component Y fails?")

    assert result["stop_reason"] == "max_iterations"
    assert result["iterations"] == AgentLoop.MAX_ITERATIONS


def test_agent_loop_stops_when_retrieval_returns_no_results():
    agent = AgentLoop(EmptyRetrievalPipeline(), FailingSufficiencyChecker())

    result = agent.run("Question with no matching evidence")

    assert result["stop_reason"] == "no_retrieval_results"
    assert result["documents"] == []
    assert result["result"] is None


def test_agent_loop_uses_one_run_id_and_original_question_every_iteration(capsys):
    checker = CapturingChecker()
    class OneDocumentPipeline:
        def query(self, query):
            return [
                RetrievalResult(
                    id="evidence",
                    text="An archive fragment.",
                    source_doc="archive",
                    chunk_index=0,
                    score=1.0,
                )
            ]

    result = AgentLoop(OneDocumentPipeline(), checker).run(
        "who is the author of the book"
    )

    assert len(set(checker.questions)) == 1
    assert checker.questions == ["who is the author of the book"] * result["iterations"]
    assert len(result["research_run_id"]) == 6
    output = capsys.readouterr().out
    assert output.count(f"[run {result['research_run_id']}] ITERATION") == result["iterations"]
