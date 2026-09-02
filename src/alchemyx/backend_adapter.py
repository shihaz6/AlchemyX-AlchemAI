"""Streamlit-facing adapter for the AlchemyX backend."""

from functools import lru_cache

from alchemyx.main import create_system


@lru_cache(maxsize=1)
def get_system():
    return create_system()


def run_research(question: str) -> dict:
    result = get_system().ask(question)
    documents = result.get("documents", [])
    sufficiency_result = result.get("sufficiency_result")
    citations = result.get("citations", [])

    return {
        "answer": result.get("answer", ""),
        "iterations": result.get("iterations", 0),
        "stop_reason": result.get("stop_reason", ""),
        "research_run_id": result.get("research_run_id", ""),
        "sufficient": (
            bool(sufficiency_result.sufficient)
            if sufficiency_result is not None
            else result.get("stop_reason") == "sufficient_evidence"
        ),
        "sources_retrieved": len(documents),
        "steps": build_steps(result),
        "sources": build_sources(documents, citations),
    }


def search_archive(query: str, top_k: int = 5) -> list[dict]:
    if not query or not query.strip():
        return []

    documents = get_system().agent.retrieval_pipeline.query(query.strip())
    return [
        {
            "id": document.id,
            "source_doc": document.source_doc,
            "chunk_index": document.chunk_index,
            "text": document.text,
            "score": document.score,
        }
        for document in documents[:top_k]
    ]


def build_steps(result: dict) -> list[dict]:
    stop_reason = result.get("stop_reason", "")
    sufficiency_result = result.get("sufficiency_result")
    return [
        {
            "id": 1,
            "status": "complete",
            "title": "Hybrid Retrieval",
            "description": "Retrieved and reranked evidence from the indexed corpus.",
            "meta": f"{len(result.get('documents', []))} sources",
        },
        {
            "id": 2,
            "status": "complete" if stop_reason == "sufficient_evidence" else "warning",
            "title": "Sufficiency Check",
            "description": (
                sufficiency_result.reason
                if sufficiency_result is not None
                else "Checked retrieved evidence for sufficiency."
            ),
            "meta": stop_reason or "complete",
        },
        {
            "id": 3,
            "status": "complete",
            "title": "Answer Generation",
            "description": "Generated the answer from the final evidence.",
            "meta": f"{result.get('iterations', 0)} iterations",
        },
    ]


def build_sources(documents, citations) -> list[dict]:
    citation_by_id = {citation["id"]: citation for citation in citations}
    return [
        {
            "id": document.id,
            "title": citation_by_id.get(document.id, {}).get("source", document.source_doc),
            "source_doc": document.source_doc,
            "chunk_index": document.chunk_index,
            "type": "Document",
            "text": document.text,
            "excerpt": document.text[:300],
            "score": document.score,
            "relevance": f"{document.score:.2f}",
        }
        for document in documents
    ]
