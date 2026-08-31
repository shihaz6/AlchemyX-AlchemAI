try:
    from .Retrieval_Result import RetrievalResult
except ImportError:
    from Retrieval_Result import RetrievalResult


class HybridSearch:
    def __init__(self, chroma_store, bm25_store, chroma_weight=0.5, bm25_weight=0.5):
        self.chroma_store = chroma_store
        self.bm25_store = bm25_store
        self.chroma_weight = chroma_weight
        self.bm25_weight = bm25_weight

    def search(self, query, top_k=5) -> list[RetrievalResult]:
        chroma_results = self.chroma_store.query(query, n_results=top_k)
        bm25_results = self.bm25_store.search(query, top_k=top_k)

        return merge_results(
            chroma_results=chroma_results,
            bm25_results=bm25_results,
            top_k=top_k,
            chroma_weight=self.chroma_weight,
            bm25_weight=self.bm25_weight,
        )

    def search_many(self, queries, top_k=5) -> list[RetrievalResult]:
        queries = list(queries)
        if not queries:
            return []

        chroma_results = self.chroma_store.search_many(queries, n_results=top_k)
        bm25_results = []
        for query in queries:
            bm25_results.extend(self.bm25_store.search(query, top_k=top_k))

        return merge_results(
            chroma_results=chroma_results,
            bm25_results=bm25_results,
            top_k=top_k,
            chroma_weight=self.chroma_weight,
            bm25_weight=self.bm25_weight,
        )


def merge_results(
    chroma_results,
    bm25_results,
    top_k=5,
    chroma_weight=0.5,
    bm25_weight=0.5,
) -> list[RetrievalResult]:
    merged_by_id = {}

    for result, score in _normalize_results(chroma_results):
        _merge_result(
            merged_by_id=merged_by_id,
            result=result,
            score=score * chroma_weight,
        )

    for result, score in _normalize_results(bm25_results):
        _merge_result(
            merged_by_id=merged_by_id,
            result=result,
            score=score * bm25_weight,
        )

    ranked_results = sorted(
        merged_by_id.values(),
        key=lambda result: result.score,
        reverse=True,
    )

    return ranked_results[:top_k]


def _merge_result(merged_by_id, result, score):
    existing_result = merged_by_id.get(result.id)
    if existing_result is None:
        merged_by_id[result.id] = RetrievalResult(
            id=result.id,
            text=result.text,
            source_doc=result.source_doc,
            chunk_index=result.chunk_index,
            score=score,
        )
        return

    existing_result.score += score


def _normalize_results(results):
    results = list(results)
    if not results:
        return []

    scores = [result.score for result in results]
    min_score = min(scores)
    max_score = max(scores)

    if min_score == max_score:
        normalized_score = 1.0 if max_score > 0 else 0.0
        return [(result, normalized_score) for result in results]

    score_range = max_score - min_score
    return [
        (result, (result.score - min_score) / score_range)
        for result in results
    ]
