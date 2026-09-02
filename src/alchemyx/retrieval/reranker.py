import time
from time import perf_counter

import voyageai

try:
    from .Retrieval_Result import RetrievalResult
    from ..config import (
        RERANK_MODEL,
        VOYAGE_MAX_RETRIES,
        VOYAGE_RETRY_BASE_SECONDS,
    )
except ImportError:
    from Retrieval_Result import RetrievalResult
    from src.alchemyx.config import (
        RERANK_MODEL,
        VOYAGE_MAX_RETRIES,
        VOYAGE_RETRY_BASE_SECONDS,
    )
try:
    from .voyage_diagnostics import log_voyage_rerank
except ImportError:
    from voyage_diagnostics import log_voyage_rerank
try:
    from ..telemetry import log
except ImportError:
    from src.alchemyx.telemetry import log


class Reranker:
    def __init__(
        self,
        api_key,
        min_relevance_score=0.0,
        max_retries=VOYAGE_MAX_RETRIES,
        retry_base_seconds=VOYAGE_RETRY_BASE_SECONDS,
    ):
        self.client = voyageai.Client(api_key=api_key)
        self.min_relevance_score = min_relevance_score
        self.max_retries = max_retries
        self.retry_base_seconds = retry_base_seconds

    def rerank(self, query, results, top_k=5, min_relevance_score=None):
        if not results:
            log("Voyage rerank bypassed=true fallback_to_bm25=false reason=no_candidates")
            return []

        threshold = (
            self.min_relevance_score
            if min_relevance_score is None
            else min_relevance_score
        )
        documents = [result.text for result in results]

        started = perf_counter()
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.rerank(
                    query=query,
                    documents=documents,
                    model=RERANK_MODEL,
                    top_k=top_k,
                )
                log_voyage_rerank(
                    model=RERANK_MODEL,
                    candidates=len(documents),
                    response=response,
                    started=started,
                )
                break
            except Exception:
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_base_seconds * (2 ** attempt))

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

        log(f"Reranking: {perf_counter() - started:.2f}s")
        return reranked
