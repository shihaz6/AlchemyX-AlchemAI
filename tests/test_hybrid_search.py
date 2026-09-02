from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult
from src.alchemyx.retrieval import hybrid_search as hybrid_search_module
from src.alchemyx.retrieval.hybrid_search import HybridSearch
from src.alchemyx.retrieval.hybrid_search import reciprocal_rank_fusion


def result(result_id):
    return RetrievalResult(
        id=result_id,
        text=result_id,
        source_doc="source",
        chunk_index=0,
        score=1.0,
    )


def test_rrf_combines_semantic_and_bm25_rankings():
    semantic = [result("A"), result("B"), result("C")]
    bm25 = [result("C"), result("A"), result("D")]

    fused = reciprocal_rank_fusion(
        ranked_result_lists=[
            (semantic, 1.0),
            (bm25, 1.0),
        ],
        top_k=4,
        rrf_k=60,
    )

    assert [item.id for item in fused[:2]] == ["A", "C"]
    assert {item.id for item in fused} == {"A", "B", "C", "D"}


def test_hybrid_search_logs_semantic_fallback_to_bm25(monkeypatch):
    logs = []

    class FailingChromaStore:
        def query(self, query, n_results):
            raise RuntimeError("semantic unavailable")

    class FakeBM25Store:
        def search(self, query, top_k):
            return [result("bm25")]

    monkeypatch.setattr(hybrid_search_module, "log", logs.append)

    search = HybridSearch(FailingChromaStore(), FakeBM25Store())
    results = search.search("question", top_k=1)

    assert [item.id for item in results] == ["bm25"]
    assert any(
        entry.startswith("Semantic retrieval bypassed=true fallback_to_bm25=true")
        for entry in logs
    )


def test_hybrid_search_adds_metadata_results_for_file_discovery_query(monkeypatch):
    logs = []

    class EmptyChromaStore:
        def query(self, query, n_results):
            return []

    class MetadataBM25Store:
        def search(self, query, top_k):
            return []

        def search_metadata(self, query, top_k):
            return [result("commit_history.csv_chunk0")]

    monkeypatch.setattr(hybrid_search_module, "log", logs.append)

    search = HybridSearch(EmptyChromaStore(), MetadataBM25Store())
    results = search.search("is there a github related file in the corpus", top_k=1)

    assert [item.id for item in results] == ["commit_history.csv_chunk0"]
    assert "Metadata retrieval bypassed=false results=1" in logs


def test_hybrid_search_uses_document_registry_for_file_discovery_query(monkeypatch):
    logs = []

    class EmptyChromaStore:
        def query(self, query, n_results):
            return []

    class EmptyBM25Store:
        def search(self, query, top_k):
            return []

        def search_metadata(self, query, top_k):
            return []

    class FakeRegistry:
        def search(self, query, top_k):
            return [result("misc/raw_data.csv_chunk0")]

    monkeypatch.setattr(hybrid_search_module, "log", logs.append)

    search = HybridSearch(EmptyChromaStore(), EmptyBM25Store(), FakeRegistry())
    results = search.search("is there a csv in the archive", top_k=1)

    assert [item.id for item in results] == ["misc/raw_data.csv_chunk0"]
    assert "Document registry retrieval bypassed=false results=1" in logs
