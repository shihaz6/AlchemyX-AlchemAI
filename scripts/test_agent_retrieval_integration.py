"""Smoke-test agent loop integration with the hybrid retrieval pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alchemyx.agent.agent_loop import AgentLoop
from alchemyx.agent.schemas import SufficiencyResult
from alchemyx.agent.hybrid_rerank_retrieval import HybridRerankRetrievalPipeline
from alchemyx.retrieval.main import (
    MIN_RERANK_SCORE,
    add_demo_documents,
    create_retrieval_stack,
)


class DemoSufficiencyChecker:
    def check(self, question, documents):
        evidence_ids = [document.id for document in documents]
        has_answer = any("Mira Quen" in document.text for document in documents)

        return SufficiencyResult(
            sufficient=has_answer,
            missing=[] if has_answer else ["Caldrin escort target"],
            search_queries=[] if has_answer else ["Caldrin escort Mira Quen"],
            evidence_ids=evidence_ids,
            reason="Demo evidence contains Caldrin's escort target."
            if has_answer
            else "Demo evidence has not found Caldrin's escort target yet.",
        )


def main():
    pipeline, bm25_store, hybrid_search, reranker = create_retrieval_stack()
    add_demo_documents(pipeline, bm25_store)

    agent_retrieval = HybridRerankRetrievalPipeline(
        hybrid_search=hybrid_search,
        reranker=reranker,
        candidate_k=15,
        top_k=5,
        min_relevance_score=MIN_RERANK_SCORE,
    )
    agent = AgentLoop(agent_retrieval, DemoSufficiencyChecker())
    result = agent.run("Who did Caldrin escort?")

    assert result["documents"], "Agent returned no retrieval documents"
    assert result["stop_reason"] == "sufficient_evidence"
    assert all(hasattr(document, "id") for document in result["documents"])
    assert all(hasattr(document, "text") for document in result["documents"])

    print("integration_ok=true")
    print(f"stop_reason={result['stop_reason']}")
    print(f"iterations={result['iterations']}")
    print(f"documents={len(result['documents'])}")


if __name__ == "__main__":
    main()
