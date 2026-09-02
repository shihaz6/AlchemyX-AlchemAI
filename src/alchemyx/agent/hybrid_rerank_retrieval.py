try:
    from .entity_resolution import boost_entity_matches
    from ..retrieval.Retrieval_Result import RetrievalResult
    from ..config import MIN_RERANK_SCORE, RERANK_CANDIDATES, RETRIEVAL_TOP_K
except ImportError:
    try:
        from alchemyx.agent.entity_resolution import boost_entity_matches
        from alchemyx.retrieval.Retrieval_Result import RetrievalResult
        from alchemyx.config import MIN_RERANK_SCORE, RERANK_CANDIDATES, RETRIEVAL_TOP_K
    except ImportError:
        from src.alchemyx.agent.entity_resolution import boost_entity_matches
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
        self.last_query_stats = {}

    def query(self, text) -> list[RetrievalResult]:
        return self.query_with_context(text, entities=[])

    def query_with_context(self, text, entities=None) -> list[RetrievalResult]:
        from time import perf_counter

        retrieval_started = perf_counter()
        candidates = self.hybrid_search.search(text, top_k=self.candidate_k)
        retrieval_seconds = perf_counter() - retrieval_started
        candidates = boost_entity_matches(candidates, entities or [])
        rerank_started = perf_counter()
        reranked = self.reranker.rerank(
            text,
            candidates,
            top_k=self.top_k,
            min_relevance_score=self.min_relevance_score,
        )
        rerank_seconds = perf_counter() - rerank_started
        self.last_query_stats = {
            "candidate_count": len(candidates),
            "reranked_count": len(reranked),
            "retrieval_seconds": retrieval_seconds,
            "rerank_seconds": rerank_seconds,
        }
        return reranked

    def query_for_adjudication(self, text, entities=None) -> list[RetrievalResult]:
        from time import perf_counter

        candidate_k = max(self.candidate_k * 2, self.top_k * 4)
        top_k = max(self.top_k * 2, self.top_k)
        retrieval_started = perf_counter()
        candidates = self.hybrid_search.search(text, top_k=candidate_k)
        retrieval_seconds = perf_counter() - retrieval_started
        candidates = boost_entity_matches(candidates, entities or [])
        rerank_started = perf_counter()
        reranked = self.reranker.rerank(
            text,
            candidates,
            top_k=top_k * 2,
            min_relevance_score=self.min_relevance_score,
        )
        rerank_seconds = perf_counter() - rerank_started
        selected = _prefer_source_diversity(reranked, top_k)
        self.last_query_stats = {
            "candidate_count": len(candidates),
            "reranked_count": len(selected),
            "retrieval_seconds": retrieval_seconds,
            "rerank_seconds": rerank_seconds,
        }
        return selected


def _prefer_source_diversity(results, top_k):
    selected = []
    deferred = []
    seen_sources = set()

    for result in results:
        if result.source_doc in seen_sources:
            deferred.append(result)
            continue
        selected.append(result)
        seen_sources.add(result.source_doc)
        if len(selected) >= top_k:
            return selected

    for result in deferred:
        selected.append(result)
        if len(selected) >= top_k:
            break
    return selected
