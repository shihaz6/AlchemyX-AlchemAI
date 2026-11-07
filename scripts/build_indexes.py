"""Build the persistent Chroma and BM25 indexes from the configured corpus."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alchemyx.ingestion.ingestion import ingest_corpus, print_ingestion_summary
from alchemyx.config import DEFAULT_CORPUS_PATH
from alchemyx.retrieval.main import create_retrieval_stack


def main():
    corpus = DEFAULT_CORPUS_PATH

    pipeline, bm25_store, hybrid_search, _reranker = create_retrieval_stack()
    result = ingest_corpus(
        corpus,
        pipeline,
        bm25_store,
        base_path=PROJECT_ROOT,
        document_registry=hybrid_search.document_registry,
    )
    print_ingestion_summary(result)

    if not result.ingested and not result.reused:
        raise RuntimeError("No documents were indexed.")


if __name__ == "__main__":
    main()
