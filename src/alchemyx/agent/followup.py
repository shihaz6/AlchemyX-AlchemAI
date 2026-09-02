import re
from dataclasses import dataclass, field
from time import perf_counter

from ..telemetry import log


AUTHORITY_SENSITIVE_TERMS = {
    "actual",
    "actually",
    "authoritative",
    "canonical",
    "correct",
    "exact",
    "official",
    "precise",
    "real",
    "true",
    "ultimately",
}

CONTESTED_TERMS = {
    "contested",
    "disputed",
    "uncertain",
    "unresolved",
    "unknown",
    "no definitive",
    "no accepted",
    "not settled",
    "contrary accounts",
    "conflicting accounts",
}

REFERENCE_PATTERNS = [
    r"consult\s+(?:the\s+)?([A-Z][A-Za-z0-9 ]{1,60})",
    r"see\s+(?:the\s+)?([A-Z][A-Za-z0-9 ]{1,60})",
    r"refer(?:red)?\s+to\s+(?:the\s+)?([A-Z][A-Za-z0-9 ]{1,60})",
    r"(?:record|records|registry|register|ledger|decree|transcript|annal|annals|codex)\s+(?:in|of|for|called|named)?\s*(?:the\s+)?([A-Z][A-Za-z0-9 ]{1,60})",
]

FACT_TERMS = {
    "date",
    "founding",
    "origin",
    "value",
    "year",
    "number",
    "count",
    "identity",
    "name",
    "location",
}

GENERIC_ENTITY_TEXT = {
    "account",
    "archive",
    "age",
    "city",
    "date",
    "entity",
    "fact",
    "question",
    "record",
    "source",
    "state",
    "value",
    "year",
}


@dataclass
class FollowupResult:
    required: bool = False
    missing: str = ""
    search_queries: list[str] = field(default_factory=list)
    reason: str = ""


def build_contested_followup(question, documents, entities, previous_queries=None):
    started = perf_counter()
    try:
        result = _build_contested_followup(question, documents, entities, previous_queries or set())
        return result
    finally:
        log(f"Follow-up query generation: {perf_counter() - started:.2f}s")


def _build_contested_followup(question, documents, entities, previous_queries):
    if not _is_authority_sensitive(question):
        return FollowupResult()
    text = "\n".join(document.text for document in documents)
    if not _is_contested(text):
        return FollowupResult()

    entity_text = _entity_text(entities, question)
    fact_text = _fact_text(question)
    references = _references(text)
    if not references:
        references = ["authoritative record"]

    queries = []
    for reference in references:
        query = " ".join(part for part in [entity_text, fact_text, reference] if part).strip()
        if query and query not in queries and query not in previous_queries:
            queries.append(query)
    fallback = " ".join(part for part in [entity_text, "exact", fact_text] if part).strip()
    if fallback and fallback not in queries and fallback not in previous_queries:
        queries.append(fallback)

    return FollowupResult(
        required=bool(queries),
        missing=f"authoritative resolution of {fact_text or 'requested fact'}",
        search_queries=queries,
        reason=(
            "Direct evidence describes the requested fact as contested or "
            "uncertain and indicates a plausible follow-up search path."
        ),
    )


def _is_authority_sensitive(question):
    terms = set(re.findall(r"\w+", question.lower()))
    return bool(terms & AUTHORITY_SENSITIVE_TERMS)


def _is_contested(text):
    lowered = text.lower()
    return any(term in lowered for term in CONTESTED_TERMS)


def _entity_text(entities, question):
    if entities:
        name = entities[0].name
        if name.lower() not in GENERIC_ENTITY_TEXT:
            return name
    quoted = re.findall(r"['\"]([^'\"]{2,80})['\"]", question)
    if quoted:
        return quoted[0]
    candidates = re.findall(
        r"\b(?:[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*)\b",
        question,
    )
    for candidate in reversed(candidates):
        words = candidate.split()
        if words and words[0] in {"What", "When", "Where", "Which", "Who", "Why", "How"}:
            words = words[1:]
        candidate = " ".join(words).strip()
        if candidate and candidate.lower() not in GENERIC_ENTITY_TEXT:
            return candidate
    return ""


def _fact_text(question):
    terms = [
        term
        for term in re.findall(r"\w+", question.lower())
        if term in FACT_TERMS
    ]
    term_set = set(terms)
    if {"founding", "year"} <= term_set:
        return "founding year"
    return " ".join(dict.fromkeys(terms))


def _references(text):
    references = []
    for pattern in REFERENCE_PATTERNS:
        for match in re.finditer(pattern, text):
            for reference in _split_references(_clean_reference(match.group(1))):
                if reference and reference not in references:
                    references.append(reference)
    return references


def _clean_reference(value):
    value = re.sub(r"\s+", " ", value).strip(" .,:;")
    value = re.sub(
        r"\b(?:as|for|to|before|after|because|which|that|where|when)\b.*$",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    return value


def _split_references(value):
    if not value:
        return []
    parts = re.split(r"\s+(?:and|or)\s+", value)
    return [part.strip(" .,:;") for part in parts if part.strip(" .,:;")]
