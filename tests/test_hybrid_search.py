from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult
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
