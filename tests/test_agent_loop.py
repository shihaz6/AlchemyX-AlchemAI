from src.alchemyx.agent.agent_loop import AgentLoop
from src.alchemyx.agent.schemas import ConflictResult, SufficiencyResult
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


class SameEvidencePipeline:
    def query(self, query):
        return [
            RetrievalResult(
                id="doc_1",
                text="Same evidence.",
                source_doc="fake",
                chunk_index=0,
                score=1.0,
            )
        ]


class NewEvidencePipeline:
    def query(self, query):
        index = 0 if query == "Question that keeps finding new evidence" else int(query.split()[-1])
        return [
            RetrievalResult(
                id=f"doc_{index}",
                text=f"Evidence {index}.",
                source_doc="fake",
                chunk_index=index,
                score=1.0,
            )
        ]


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


class OneStrongSourceChecker:
    def __init__(self):
        self.calls = 0

    def check(self, question, documents):
        self.calls += 1
        return SufficiencyResult(
            sufficient=True,
            missing=[],
            search_queries=[],
            evidence_ids=[documents[0].id],
            reason="One direct source answers the question.",
        )


class ConflictAwareChecker:
    def check(self, question, documents):
        return SufficiencyResult(
            sufficient=True,
            missing=[],
            search_queries=[],
            evidence_ids=[document.id for document in documents],
            reason="Initial checker sees relevant evidence.",
        )


class ScriptedConflictAdjudicator:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def should_adjudicate(self, question, documents, sufficiency_result):
        return True

    def adjudicate(self, question, documents, sufficiency_result):
        self.calls.append((question, [document.id for document in documents]))
        index = min(len(self.calls) - 1, len(self.results) - 1)
        return self.results[index]


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
        NewEvidencePipeline(),
        NeverSufficientChecker(),
    )

    result = agent.run("Question that keeps finding new evidence")

    assert result["stop_reason"] == "max_iterations"
    assert result["iterations"] == AgentLoop.MAX_ITERATIONS


def test_agent_loop_stops_when_followup_adds_no_new_evidence():
    checker = NeverSufficientChecker()
    agent = AgentLoop(SameEvidencePipeline(), checker)

    result = agent.run("Question that keeps finding same evidence")

    assert result["stop_reason"] == "no_new_evidence"
    assert result["iterations"] == 2
    assert checker.calls == 1


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
    assert checker.questions == ["who is the author of the book"]
    assert len(result["research_run_id"]) == 6
    output = capsys.readouterr().out
    assert output.count(f"[run {result['research_run_id']}] ITERATION") == result["iterations"]


def test_agent_loop_simple_no_conflict_stops_in_one_iteration():
    class Pipeline:
        def query(self, query):
            return [
                RetrievalResult(
                    id="source_a_chunk0",
                    text="Object Q has measured value 42.",
                    source_doc="source_a.txt",
                    chunk_index=0,
                    score=1.0,
                )
            ]

    checker = OneStrongSourceChecker()
    result = AgentLoop(Pipeline(), checker).run("What is Object Q's measured value?")

    assert result["iterations"] == 1
    assert result["stop_reason"] == "sufficient_evidence"
    assert result["result"].sufficient is True
    assert checker.calls == 1


def test_agent_loop_requeries_to_resolve_conflict():
    class Pipeline:
        def __init__(self):
            self.queries = []

        def query(self, query):
            self.queries.append(("normal", query))
            if query == "What is the actual calibration value for Device Z?":
                return [
                    RetrievalResult("a_chunk0", "A note says Device Z is 17.", "note_a.txt", 0, 1.0),
                    RetrievalResult("b_chunk0", "A memo says Device Z is 19.", "memo_b.txt", 0, 0.9),
                    RetrievalResult(
                        "c_chunk0",
                        "The memo says consult Register R for the official value.",
                        "pointer_c.txt",
                        0,
                        0.8,
                    ),
                ]
            return []

        def query_for_adjudication(self, query):
            self.queries.append(("adjudication", query))
            return [
                RetrievalResult(
                    "d_chunk0",
                    "Register R is the official record. It gives Device Z as 19 and rejects 17 as a popular error.",
                    "register_r.txt",
                    0,
                    1.0,
                )
            ]

    adjudicator = ScriptedConflictAdjudicator(
        [
            ConflictResult(
                has_conflict=True,
                claim="calibration value for Device Z",
                candidate_values=["17", "19"],
                supporting_evidence_ids={"17": ["a_chunk0"], "19": ["b_chunk0"]},
                authority_notes=["A retrieved source points to Register R."],
                recommended_search_queries=["Register R official Device Z calibration value"],
                resolvable=True,
                resolved=False,
                reason="The conflict needs the referenced register.",
            ),
            ConflictResult(
                has_conflict=True,
                claim="calibration value for Device Z",
                candidate_values=["17", "19"],
                supporting_evidence_ids={"17": ["a_chunk0"], "19": ["b_chunk0", "d_chunk0"]},
                authority_notes=["Register R explicitly rejects the alternative value."],
                resolvable=True,
                resolved=True,
                selected_value="19",
                selected_evidence_ids=["d_chunk0"],
                reason="Register R directly resolves the conflict in favor of 19.",
            ),
        ]
    )

    pipeline = Pipeline()
    result = AgentLoop(
        pipeline,
        ConflictAwareChecker(),
        evidence_adjudicator=adjudicator,
    ).run("What is the actual calibration value for Device Z?")

    assert result["iterations"] == 2
    assert result["stop_reason"] == "sufficient_evidence"
    assert result["result"].evidence_ids == ["d_chunk0", "a_chunk0", "b_chunk0"]
    assert pipeline.queries[1] == (
        "adjudication",
        "Register R official Device Z calibration value",
    )


def test_agent_loop_prefers_explicit_correction_authority_signal():
    class Pipeline:
        def query(self, query):
            return [
                RetrievalResult("popular_chunk0", "A popular account gives Sample N as blue.", "popular.txt", 0, 1.0),
                RetrievalResult(
                    "correction_chunk0",
                    "The canonical correction states Sample N is green, not blue.",
                    "correction.txt",
                    0,
                    1.0,
                ),
            ]

    adjudicator = ScriptedConflictAdjudicator(
        [
            ConflictResult(
                has_conflict=True,
                claim="true color of Sample N",
                candidate_values=["blue", "green"],
                supporting_evidence_ids={
                    "blue": ["popular_chunk0"],
                    "green": ["correction_chunk0"],
                },
                authority_notes=["One source explicitly corrects the popular account."],
                resolvable=True,
                resolved=True,
                selected_value="green",
                selected_evidence_ids=["correction_chunk0"],
                reason="The correcting source directly rejects the alternative.",
            )
        ]
    )

    result = AgentLoop(
        Pipeline(),
        ConflictAwareChecker(),
        evidence_adjudicator=adjudicator,
    ).run("What is the true color of Sample N?")

    assert result["iterations"] == 1
    assert result["result"].sufficient is True
    assert result["result"].conflict_result.selected_value == "green"


def test_agent_loop_genuine_unresolved_conflict_remains_insufficient():
    class Pipeline:
        def __init__(self):
            self.calls = 0

        def query(self, query):
            self.calls += 1
            return [
                RetrievalResult("left_chunk0", "Record Left gives Vessel P as 8.", "left.txt", 0, 1.0),
                RetrievalResult("right_chunk0", "Record Right gives Vessel P as 9.", "right.txt", 0, 1.0),
            ]

    adjudicator = ScriptedConflictAdjudicator(
        [
            ConflictResult(
                has_conflict=True,
                claim="count for Vessel P",
                candidate_values=["8", "9"],
                supporting_evidence_ids={"8": ["left_chunk0"], "9": ["right_chunk0"]},
                authority_notes=["Both records are direct and no higher-authority source is available."],
                recommended_search_queries=[],
                resolvable=False,
                resolved=False,
                reason="The supplied evidence remains genuinely unresolved.",
            )
        ]
    )

    result = AgentLoop(
        Pipeline(),
        ConflictAwareChecker(),
        evidence_adjudicator=adjudicator,
    ).run("What is the exact count for Vessel P?")

    assert result["stop_reason"] == "no_search_query"
    assert result["result"].sufficient is False
    assert "count for Vessel P" in result["result"].missing


def test_agent_loop_uses_broader_source_diverse_retrieval_for_conflict_followup():
    class Pipeline:
        def __init__(self):
            self.used_adjudication_search = False

        def query(self, query):
            return [
                RetrievalResult("one_chunk0", "File One says Gauge L is 3.", "one.txt", 0, 1.0),
                RetrievalResult("one_chunk1", "File One repeats Gauge L is 3.", "one.txt", 1, 0.9),
                RetrievalResult("two_chunk0", "File Two says Gauge L is 4.", "two.txt", 0, 0.8),
            ]

        def query_for_adjudication(self, query):
            self.used_adjudication_search = True
            return [
                RetrievalResult("three_chunk0", "File Three reviews Gauge L but does not resolve it.", "three.txt", 0, 0.9)
            ]

    adjudicator = ScriptedConflictAdjudicator(
        [
            ConflictResult(
                has_conflict=True,
                claim="Gauge L value",
                candidate_values=["3", "4"],
                supporting_evidence_ids={"3": ["one_chunk0"], "4": ["two_chunk0"]},
                recommended_search_queries=["additional independent Gauge L records"],
                resolvable=True,
                resolved=False,
                reason="Evidence is dominated by too few source families.",
            ),
            ConflictResult(
                has_conflict=True,
                claim="Gauge L value",
                candidate_values=["3", "4"],
                supporting_evidence_ids={"3": ["one_chunk0"], "4": ["two_chunk0"]},
                recommended_search_queries=[],
                resolvable=False,
                resolved=False,
                reason="No more useful source-diverse path is available.",
            ),
        ]
    )

    pipeline = Pipeline()
    result = AgentLoop(
        pipeline,
        ConflictAwareChecker(),
        evidence_adjudicator=adjudicator,
    ).run("What is the actual Gauge L value?")

    assert pipeline.used_adjudication_search is True
    assert result["stop_reason"] == "no_search_query"
