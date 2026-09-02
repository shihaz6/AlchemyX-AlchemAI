"""Streamlit-facing adapter for the AlchemyX backend."""

from functools import lru_cache
from pathlib import Path
import re

from alchemyx.agent.evidence_adjudicator import source_family_id
from alchemyx.main import create_system


@lru_cache(maxsize=1)
def get_system():
    return create_system()


def run_research(question: str) -> dict:
    result = get_system().ask(question)
    documents = result.get("documents", [])
    sufficiency_result = result.get("sufficiency_result")
    citations = result.get("citations", [])
    answer_evidence_ids = result.get("answer_evidence_ids", [])
    all_sources = build_sources(
        documents,
        citations,
        sufficiency_result,
        answer_evidence_ids=answer_evidence_ids,
    )
    sources = [source for source in all_sources if source["visibility"] == "evidence"]
    related_sources = [source for source in all_sources if source["visibility"] == "context"]
    excluded_sources = [source for source in all_sources if source["visibility"] == "excluded"]
    timings = build_timings(result)
    safe_answer = _user_safe_text(result.get("answer", ""))
    timeline = build_timeline(result.get("timeline", []))
    conflict = build_conflict_summary(sufficiency_result, sources, timeline)

    return {
        "answer": safe_answer,
        "clean_answer": clean_answer(safe_answer, sources),
        "iterations": result.get("iterations", 0),
        "stop_reason": result.get("stop_reason", ""),
        "stop_reason_label": humanize_status(result.get("stop_reason", "")),
        "research_run_id": result.get("research_run_id", ""),
        "sufficient": (
            bool(sufficiency_result.sufficient)
            if sufficiency_result is not None
            else result.get("stop_reason") == "sufficient_evidence"
        ),
        "conflict": conflict,
        "sources_retrieved": len(sources),
        "chunks_retrieved": len(documents),
        "timeline": timeline,
        "timings": timings,
        "steps": build_steps(result),
        "sources": sources,
        "related_sources": related_sources,
        "excluded_sources": excluded_sources,
        "technical_sources": build_technical_sources(documents, citations),
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
            "rank_score": document.score,
            "score_type": "rank_score",
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


def build_sources(documents, citations, sufficiency_result=None, answer_evidence_ids=None) -> list[dict]:
    citation_by_id = {citation["id"]: citation for citation in citations}
    conflict_result = getattr(sufficiency_result, "conflict_result", None)
    selected_ids = set(getattr(conflict_result, "selected_evidence_ids", []) or [])
    answer_ids = set(answer_evidence_ids or [])
    sufficiency_ids = set(getattr(sufficiency_result, "evidence_ids", []) or [])
    conflicted_ids = set()
    claims_by_id = {}
    if conflict_result is not None:
        for claim, evidence_ids in conflict_result.supporting_evidence_ids.items():
            for evidence_id in evidence_ids:
                conflicted_ids.add(evidence_id)
                claims_by_id[evidence_id] = claim

    usable_matches = {"exact_match", "alias_match", "valid_contextual_match"}
    selected_ids = {
        document.id for document in documents
        if document.id in selected_ids and _document_is_usable(document, claims_by_id.get(document.id))
    }

    grouped = {}
    for document in documents:
        family_id = source_family_id(document.source_doc)
        source_name = citation_by_id.get(document.id, {}).get("source", document.source_doc)
        source = grouped.setdefault(
            family_id,
            {
                "source_family_id": family_id,
                "title": readable_source_label(source_name),
                "document_type": readable_document_type(source_name),
                "formats": [],
                "claim": "",
                "role": "supporting",
                "authority_assessment": "Available evidence",
                "authority_summary": "",
                "reason": "",
                "chunk_ids": [],
                "chunks": 0,
                "chunk_numbers": [],
                "excerpt": "",
                "technical_details": [],
                "entity_match": "unknown",
                "used_for_direct_claim": False,
                "visibility": "excluded",
                "usable_chunk_ids": [],
                "excluded_chunk_ids": [],
            },
        )
        extension = Path(document.source_doc).suffix.lower().lstrip(".")
        if extension and extension.upper() not in source["formats"]:
            source["formats"].append(extension.upper())
        source["chunk_ids"].append(document.id)
        source["chunks"] += 1
        if document.chunk_index not in source["chunk_numbers"]:
            source["chunk_numbers"].append(document.chunk_index)
        if not source["excerpt"]:
            source["excerpt"] = document.text[:300]
        source["technical_details"].append(
            {
                "id": document.id,
                "source_doc": document.source_doc,
                "chunk_index": document.chunk_index,
                "score": document.score,
            }
        )
        entity_match = getattr(document, "entity_match", None)
        if entity_match is not None:
            claim_match = _document_is_usable(document, claims_by_id.get(document.id))
            effective_match = entity_match.entity_match
            if claim_match and effective_match not in usable_matches:
                effective_match = "exact_match"
            if effective_match in usable_matches or entity_match.usable_for_direct_claim:
                source["usable_chunk_ids"].append(document.id)
            else:
                source["excluded_chunk_ids"].append(document.id)
            if effective_match in usable_matches:
                source["entity_match"] = readable_entity_match(effective_match)
            elif source["entity_match"] == "unknown":
                source["entity_match"] = readable_entity_match(entity_match.entity_match)
            source["used_for_direct_claim"] = bool(source["usable_chunk_ids"])
            if effective_match == "related_entity":
                source["visibility"] = "context"
        if document.id in claims_by_id and not source["claim"]:
            source["claim"] = claims_by_id[document.id]
        material_id = (
            document.id in selected_ids
            or document.id in answer_ids
            or document.id in sufficiency_ids
            or document.id in conflicted_ids
        )
        if material_id and (
            getattr(document, "entity_match", None) is None
            or document.id in source["usable_chunk_ids"]
        ):
            source["visibility"] = "evidence"
        if document.id in selected_ids or document.id in answer_ids:
            source["role"] = "selected / resolving"
            source["authority_assessment"] = "Strong"
        elif document.id in conflicted_ids and source["role"] != "selected / resolving":
            source["role"] = "conflicting"
            source["authority_assessment"] = "Lower or unresolved"

    for source in grouped.values():
        if conflict_result is not None:
            if source["role"] == "selected / resolving":
                source["authority_summary"] = _user_safe_text(_first_text(conflict_result.authority_notes))
                source["reason"] = _user_safe_text(conflict_result.reason)
            elif source["role"] == "conflicting":
                source["reason"] = "Supports a competing claim considered during adjudication."
        source["formats"].sort()
        source["chunk_numbers"].sort()
        source.pop("usable_chunk_ids", None)
        source.pop("excluded_chunk_ids", None)

    return sorted(
        grouped.values(),
        key=lambda source: (
            0 if source["role"] == "selected" else 1 if source["role"] == "conflicting" else 2,
            source["title"].lower(),
        ),
    )


def _document_is_usable(document, claim=""):
    match = getattr(document, "entity_match", None)
    if match is None:
        return True
    if match.entity_match in {"exact_match", "alias_match", "valid_contextual_match"}:
        return True
    # Supports legacy/custom callers that omitted entity annotation but gave
    # a claim whose requested subject is explicitly present in the chunk.
    return bool(claim and str(claim).lower() in str(document.text).lower())


def build_technical_sources(documents, citations) -> list[dict]:
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
            "rank_score": document.score,
            "score_type": "rank_score",
            "relevance": f"rank {document.score:.2f}",
        }
        for document in documents
    ]


def build_conflict_summary(sufficiency_result, sources=None, timeline=None) -> dict:
    conflict_result = getattr(sufficiency_result, "conflict_result", None)
    conflict_state = canonical_conflict_state(conflict_result, timeline or [])
    if conflict_result is None or not conflict_result.has_conflict:
        return {
            "detected": False,
            "resolved": False,
            "state": conflict_state,
            "status": conflict_state_label(conflict_state),
            "candidate_values": [],
            "resolution_summary": "",
            "selected_value": "",
            "competing_claims": [],
        }

    title_by_chunk = {}
    for source in sources or []:
        for chunk_id in source.get("chunk_ids", []):
            title_by_chunk[chunk_id] = source.get("title", chunk_id)

    competing_claims = []
    for value, evidence_ids in conflict_result.supporting_evidence_ids.items():
        labels = []
        for evidence_id in evidence_ids:
            label = title_by_chunk.get(evidence_id, evidence_id)
            if label not in labels:
                labels.append(label)
        competing_claims.append(
            {
                "value": value,
                "sources": labels,
                "evidence_ids": list(evidence_ids),
            }
        )

    return {
        "detected": True,
        "resolved": bool(conflict_result.resolved),
        "state": conflict_state,
        "status": conflict_state_label(conflict_state),
        "candidate_values": list(conflict_result.candidate_values),
        "resolution_summary": _user_safe_text(conflict_result.reason),
        "selected_value": conflict_result.selected_value,
        "authority_notes": list(conflict_result.authority_notes),
        "competing_claims": competing_claims,
    }


def canonical_conflict_state(conflict_result, timeline):
    if conflict_result is not None and conflict_result.has_conflict:
        if conflict_result.resolved:
            return "resolved"
        return "unresolved"
    if any(entry.get("conflict_resolved") for entry in timeline):
        return "resolved"
    if any(entry.get("conflict_detected") for entry in timeline):
        return "detected"
    return "none"


def conflict_state_label(state):
    return {
        "none": "None",
        "detected": "Detected",
        "resolved": "Resolved",
        "unresolved": "Unresolved",
    }.get(state, "None")


def build_timeline(timeline) -> list[dict]:
    entries = []
    for entry in sorted(timeline, key=lambda item: item.get("iteration", 0)):
        conflict_detected = bool(entry.get("conflict_detected"))
        conflict_resolved = bool(entry.get("conflict_resolved"))
        if conflict_resolved:
            conflict_status = "Resolved"
        elif conflict_detected:
            conflict_status = "Detected"
        else:
            conflict_status = "None"
        entries.append(
            {
                "iteration": entry.get("iteration"),
                "query": entry.get("query", ""),
                "retrieved": entry.get("retrieved", 0),
                "reranked": entry.get("reranked", 0),
                "distinct_sources": entry.get("distinct_sources", 0),
                "new_evidence": entry.get("new_evidence", 0),
                "new_evidence_summary": entry.get("new_evidence_summary", ""),
                "conflict_detected": conflict_detected,
                "conflict_resolved": conflict_resolved,
                "conflict_status": conflict_status,
                "candidate_values": entry.get("candidate_values", []),
                "missing": _user_safe_missing(entry.get("missing", [])),
                "next_queries": entry.get("next_queries", []),
                "sufficient": bool(entry.get("sufficient")),
                "sufficiency_label": "Yes" if entry.get("sufficient") else "No",
                "stop_reason": entry.get("stop_reason", ""),
                "stop_reason_label": humanize_status(entry.get("stop_reason", "")),
                "elapsed_seconds": entry.get("elapsed_seconds"),
                "retrieval_seconds": entry.get("retrieval_seconds"),
                "rerank_seconds": entry.get("rerank_seconds"),
                "sufficiency_seconds": entry.get("sufficiency_seconds"),
                "adjudication_seconds": entry.get("adjudication_seconds"),
                "followup_seconds": entry.get("followup_seconds"),
            }
        )
    return entries


def build_timings(result):
    timings = result.get("timings", {}) or {}
    return {
        "agent_loop": timings.get("agent_loop"),
        "entity_extraction": timings.get("entity_extraction"),
        "entity_validation": timings.get("entity_validation"),
        "retrieval": _sum_timeline_seconds(result, "retrieval_seconds"),
        "reranking": _sum_timeline_seconds(result, "rerank_seconds"),
        "sufficiency": _sum_timeline_seconds(result, "sufficiency_seconds"),
        "adjudication": _sum_timeline_seconds(result, "adjudication_seconds"),
        "followup_query_generation": _sum_timeline_seconds(result, "followup_seconds"),
        "final_generation": timings.get("final_generation"),
        "end_to_end": timings.get("end_to_end"),
    }


def clean_answer(answer, sources=None):
    cleaned = str(answer or "")
    chunk_label_by_id = {}
    for source in sources or []:
        for chunk_id in source.get("chunk_ids", []):
            chunk_label_by_id[chunk_id] = source.get("title", chunk_id)

    def replace_ids(match):
        ids = [part.strip() for part in match.group(1).split(",")]
        labels = []
        for evidence_id in ids:
            label = chunk_label_by_id.get(evidence_id)
            if label and label not in labels:
                labels.append(label)
        if not labels:
            return ""
        return "[" + "; ".join(labels[:3]) + "]"

    cleaned = re.sub(r"\[([A-Za-z0-9_./ ·,-]+_chunk\d+(?:\s*,\s*[A-Za-z0-9_./ ·,-]+_chunk\d+)*)\]", replace_ids, cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def readable_source_label(source_doc):
    path = Path(str(source_doc).replace("\\", "/"))
    name = path.name
    for suffix in Path(name).suffixes:
        name = name[: -len(suffix)]
    name = re.sub(r"(?i)(?:[._-]?scan)$", "", name)
    words = re.split(r"[_\-]+", name)
    roman = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
    small = {"a", "an", "and", "as", "for", "in", "of", "on", "or", "the", "to"}
    titled = []
    for index, word in enumerate(words):
        lower = word.lower()
        if lower in roman:
            titled.append(lower.upper())
        elif index > 0 and lower in small:
            titled.append(lower)
        else:
            titled.append(lower.capitalize())
    return " ".join(titled) or str(source_doc)


def readable_document_type(source_doc):
    path = Path(str(source_doc))
    extension = path.suffix.lower().lstrip(".")
    if extension:
        return extension.upper()
    return "Document"


def humanize_status(status):
    labels = {
        "sufficient_evidence": "Sufficient evidence",
        "no_retrieval_results": "No retrieval results",
        "no_new_evidence": "No new evidence",
        "no_search_query": "No useful follow-up",
        "repeated_query": "Repeated query avoided",
        "max_iterations": "Max iterations reached",
    }
    if not status:
        return ""
    return labels.get(status, str(status).replace("_", " ").capitalize())


def readable_entity_match(value):
    labels = {
        "exact_match": "Exact",
        "alias_match": "Alias",
        "related_entity": "Related",
        "ambiguous": "Ambiguous",
        "mismatch": "Excluded",
    }
    return labels.get(value, "Unknown")


def _first_text(values):
    for value in values or []:
        if value:
            return value
    return ""


def _sum_timeline_seconds(result, key):
    values = [
        entry.get(key)
        for entry in result.get("timeline", []) or []
        if entry.get(key) is not None
    ]
    if not values:
        return None
    return sum(values)


def _user_safe_missing(values):
    internal_markers = ("usable sufficiency assessment", "invalid json", "malformed")
    return [
        value for value in (values or [])
        if isinstance(value, str)
        and not any(marker in value.lower() for marker in internal_markers)
    ]


def _user_safe_text(value):
    text = str(value or "")
    markers = ("usable sufficiency assessment", "invalid json", "malformed output")
    return "" if any(marker in text.lower() for marker in markers) else text
