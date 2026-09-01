try:
    from ..retrieval.Retrieval_Result import RetrievalResult
except ImportError:
    try:
        from alchemyx.retrieval.Retrieval_Result import RetrievalResult
    except ImportError:
        from src.alchemyx.retrieval.Retrieval_Result import RetrievalResult


class HybridRerankRetrievalPipeline:
    def __init__(
        self,
        hybrid_search,
        reranker,
        candidate_k=15,
        top_k=5,
        min_relevance_score=0.5,
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
