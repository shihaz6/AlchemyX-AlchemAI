from src.alchemyx.agent.hybrid_rerank_retrieval import HybridRerankRetrievalPipeline
from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult
from src.alchemyx.retrieval import main as retrieval_main
from src.alchemyx.retrieval.main import create_agent_retrieval_pipeline


class FakeHybridSearch:
    def __init__(self):
        self.calls = []
        self.results = [
            RetrievalResult(
                id="doc_1_chunk0",
                text="first candidate",
                source_doc="doc_1",
                chunk_index=0,
                score=0.4,
            )
        ]

    def search(self, query, top_k=5):
        self.calls.append((query, top_k))
        return self.results


class FakeReranker:
    def __init__(self):
        self.calls = []
        self.results = [
            RetrievalResult(
                id="doc_1_chunk0",
                text="first candidate",
                source_doc="doc_1",
                chunk_index=0,
                score=0.91,
            )
        ]

    def rerank(self, query, results, top_k=5, min_relevance_score=None):
        self.calls.append((query, results, top_k, min_relevance_score))
        return self.results


def test_query_runs_hybrid_search_then_reranker():
    hybrid_search = FakeHybridSearch()
    reranker = FakeReranker()
    pipeline = HybridRerankRetrievalPipeline(
        hybrid_search=hybrid_search,
        reranker=reranker,
        candidate_k=12,
        top_k=3,
        min_relevance_score=0.7,
    )

    results = pipeline.query("Where did Mira go?")

    assert results == reranker.results
    assert all(isinstance(result, RetrievalResult) for result in results)
    assert hybrid_search.calls == [("Where did Mira go?", 12)]
    assert reranker.calls == [
        ("Where did Mira go?", hybrid_search.results, 3, 0.7)
    ]


def test_adjudication_query_uses_broader_pool_and_prefers_source_diversity():
    hybrid_search = FakeHybridSearch()
    hybrid_search.results = [
        RetrievalResult("a_chunk0", "first", "same.txt", 0, 1.0),
        RetrievalResult("a_chunk1", "second", "same.txt", 1, 0.9),
        RetrievalResult("b_chunk0", "third", "other.txt", 0, 0.8),
    ]
    reranker = FakeReranker()
    reranker.results = hybrid_search.results
    pipeline = HybridRerankRetrievalPipeline(
        hybrid_search=hybrid_search,
        reranker=reranker,
        candidate_k=12,
        top_k=2,
        min_relevance_score=0.7,
    )

    results = pipeline.query_for_adjudication("Where did Mira go?")

    assert hybrid_search.calls == [("Where did Mira go?", 24)]
    assert reranker.calls == [
        ("Where did Mira go?", hybrid_search.results, 8, 0.7)
    ]
    assert [result.source_doc for result in results[:2]] == ["same.txt", "other.txt"]


def test_agent_retrieval_pipeline_requires_built_indexes(monkeypatch):
    class EmptyCollection:
        def count(self):
            return 0

    class EmptyPipeline:
        collection = EmptyCollection()

    class EmptyBM25:
        documents = []

    monkeypatch.setattr(
        retrieval_main,
        "create_retrieval_stack",
        lambda api_key=None: (EmptyPipeline(), EmptyBM25(), None, None),
    )

    try:
        create_agent_retrieval_pipeline(api_key="test-key")
    except RuntimeError as exc:
        assert "build_indexes.py" in str(exc)
    else:
        raise AssertionError("Expected missing corpus path to raise RuntimeError")
