try:
    from ..retrieval.Retrieval_Result import RetrievalResult
    from ..config import MIN_RERANK_SCORE, RERANK_CANDIDATES, RETRIEVAL_TOP_K
except ImportError:
    try:
        from alchemyx.retrieval.Retrieval_Result import RetrievalResult
        from alchemyx.config import MIN_RERANK_SCORE, RERANK_CANDIDATES, RETRIEVAL_TOP_K
    except ImportError:
        from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult
        from src.alchemyx.config import MIN_RERANK_SCORE, RERANK_CANDIDATES, RETRIEVAL_TOP_K


class HybridRerankRetrievalPipeline:
    def __init__(
        self,
        hybrid_search,
        reranker,
        candidate_k=RERANK_CANDIDATES,
        top_k=RETRIEVAL_TOP_K,
        min_relevance_score=MIN_RERANK_SCORE,
    ):
        self.hybrid_search = hybrid_search
        self.reranker = reranker
        self.candidate_k = candidate_k
        self.top_k = top_k
        self.min_relevance_score = min_relevance_score

    def query(self, text) -> list[RetrievalResult]:
        candidates = self.hybrid_search.search(text, top_k=self.candidate_k)
        return self.reranker.rerank(
            text,
            candidates,
            top_k=self.top_k,
            min_relevance_score=self.min_relevance_score,
        )
