import voyageai

try:
    from .Retrieval_Result import RetrievalResult
except ImportError:
    from Retrieval_Result import RetrievalResult


class Reranker:
    def __init__(self, api_key, min_relevance_score=0.0):
        self.client = voyageai.Client(api_key=api_key)
        self.min_relevance_score = min_relevance_score

    def rerank(self, query, results, top_k=5, min_relevance_score=None):
        if not results:
            return []

        threshold = (
            self.min_relevance_score
            if min_relevance_score is None
            else min_relevance_score
        )
        documents = [result.text for result in results]

        response = self.client.rerank(
            query=query,
            documents=documents,
            model="rerank-2.5",
            top_k=top_k,
        )

        reranked = []

        for item in response.results:
            result = results[item.index]
            score = item.relevance_score
            if score < threshold:
                continue

            reranked.append(
                RetrievalResult(
                    id=result.id,
                    text=result.text,
                    source_doc=result.source_doc,
                    chunk_index=result.chunk_index,
                    score=score,
                )
            )

        return reranked
