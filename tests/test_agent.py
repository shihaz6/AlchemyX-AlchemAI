from unittest.mock import Mock

from alchemyx.agent.agent_loop import AgentLoop
from alchemyx.agent.schemas import SufficiencyResult
from alchemyx.retrieval.Retrieval_Result import RetrievalResult


def test_no_evidence_stops_without_calling_llm():
    class Retrieval:
        def query(self, question):
            return []

    checker = Mock()
    result = AgentLoop(Retrieval(), checker).run("What is recorded?")
    assert result["stop_reason"] == "no_retrieval_results"
    assert result["documents"] == []
    checker.check.assert_not_called()


def test_sufficient_evidence_stops_first_iteration():
    document = RetrievalResult("doc1", "The answer is seven.", "doc.txt", 0, 1.0)

    class Retrieval:
        def query(self, question):
            return [document]

    checker = Mock(last_duration=0.0)
    checker.check.return_value = SufficiencyResult(True, [], [], ["doc1"], "Supported")
    result = AgentLoop(Retrieval(), checker).run("What is recorded?")
    assert result["stop_reason"] == "sufficient_evidence"
    assert result["iterations"] == 1
    checker.check.assert_called_once()
