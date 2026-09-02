"""Build the persistent Chroma and BM25 indexes from the configured corpus."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import find_dotenv, load_dotenv

from alchemyx.ingestion.ingestion import ingest_corpus, print_ingestion_summary
from alchemyx.retrieval.main import create_retrieval_stack


def main():
    dotenv_path = find_dotenv(str(PROJECT_ROOT / ".env"))
    load_dotenv(dotenv_path)
    corpus = os.getenv("ALCHEMYX_CORPUS_PATH")
    if not corpus:
        raise RuntimeError("ALCHEMYX_CORPUS_PATH is missing from .env")

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
