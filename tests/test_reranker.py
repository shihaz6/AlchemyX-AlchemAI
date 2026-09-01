from dataclasses import dataclass

from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult
from src.alchemyx.retrieval import reranker as reranker_module
from src.alchemyx.retrieval.reranker import Reranker


@dataclass
class FakeRerankItem:
    index: int
    relevance_score: float


class FakeRerankResponse:
    def __init__(self, results):
        self.results = results


class FakeVoyageClient:
    calls = []

    def __init__(self, api_key):
        self.api_key = api_key

    def rerank(self, query, documents, model, top_k):
        self.calls.append(
            {
                "query": query,
                "documents": documents,
                "model": model,
                "top_k": top_k,
            }
        )
        scored = [
            FakeRerankItem(index=0, relevance_score=0.9),
            FakeRerankItem(index=1, relevance_score=0.4),
            FakeRerankItem(index=2, relevance_score=0.8),
        ]
        return FakeRerankResponse(scored[:top_k])


def make_results():
    return [
        RetrievalResult("A", "alpha", "source", 0, 0.1),
        RetrievalResult("B", "beta", "source", 1, 0.2),
        RetrievalResult("C", "gamma", "source", 2, 0.3),
    ]


def test_reranker_filters_results_below_threshold(monkeypatch):
    FakeVoyageClient.calls = []
    monkeypatch.setattr(reranker_module.voyageai, "Client", FakeVoyageClient)
    reranker = Reranker(api_key="test")

    results = reranker.rerank(
        "question",
        make_results(),
        top_k=3,
        min_relevance_score=0.5,
    )

    assert [result.id for result in results] == ["A", "C"]


def test_reranker_respects_top_k(monkeypatch):
    FakeVoyageClient.calls = []
    monkeypatch.setattr(reranker_module.voyageai, "Client", FakeVoyageClient)
    reranker = Reranker(api_key="test")

    results = reranker.rerank("question", make_results(), top_k=1)

    assert [result.id for result in results] == ["A"]
    assert FakeVoyageClient.calls[0]["top_k"] == 1


def test_reranker_empty_input_returns_empty_list(monkeypatch):
    FakeVoyageClient.calls = []
    monkeypatch.setattr(reranker_module.voyageai, "Client", FakeVoyageClient)
    reranker = Reranker(api_key="test")

    assert reranker.rerank("question", []) == []
    assert FakeVoyageClient.calls == []
