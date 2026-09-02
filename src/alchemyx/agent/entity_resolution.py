import re
from pathlib import Path
from time import perf_counter

from .schemas import Entity, EntityMatchResult
from ..telemetry import log


QUESTION_WORDS = {
    "How",
    "In",
    "Is",
    "List",
    "Name",
    "Tell",
    "The",
    "What",
    "When",
    "Where",
    "Which",
    "Who",
    "Why",
}

FACT_TERMS = {
    "actual",
    "answer",
    "authoritative",
    "date",
    "exact",
    "fact",
    "founding",
    "official",
    "precise",
    "real",
    "true",
    "value",
    "year",
}

GENERIC_SINGLE_ENTITY_WORDS = {
    "Account",
    "Archive",
    "Age",
    "City",
    "Codex",
    "Date",
    "Decree",
    "Entity",
    "Fact",
    "Ledger",
    "Question",
    "Record",
    "Register",
    "Registry",
    "Report",
    "Source",
    "State",
    "Transcript",
    "Value",
    "Year",
}

RELATION_TERMS = {
    "between",
    "compare",
    "connected",
    "connection",
    "near",
    "nearby",
    "relationship",
    "related",
}


class EntityResolver:
    def extract(self, question):
        started = perf_counter()
        entities = _extract_question_entities(question)
        log(f"Entity extraction: {perf_counter() - started:.2f}s")
        return entities

    def validate_documents(self, entities, documents):
        started = perf_counter()
        matches = {}
        if not entities:
            log(f"Entity validation: {perf_counter() - started:.2f}s")
            return matches

        aliases_by_entity = _extract_aliases(entities, documents)
        for entity in entities:
            entity.aliases = aliases_by_entity.get(entity.name, entity.aliases)

        for document in documents:
            match = _validate_document(entities, document)
            matches[document.id] = match

        log(f"Entity validation: {perf_counter() - started:.2f}s")
        return matches

    def direct_documents(self, question, documents, matches):
        if not matches or _allows_related_entities(question) or not _requires_entity_consistency(question):
            return documents
        direct = [
            document
            for document in documents
            if matches.get(document.id)
            and matches[document.id].usable_for_direct_claim
        ]
        return direct or documents


def _extract_question_entities(question):
    quoted = re.findall(r"['\"]([^'\"]{2,80})['\"]", question)
    candidates = []
    candidates.extend(quoted)
    candidates.extend(
        match.group(0)
        for match in re.finditer(
            r"\b(?:[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*)\b",
            question,
        )
    )

    entities = []
    seen = set()
    for candidate in candidates:
        name = _clean_candidate(candidate)
        if not name:
            continue
        first = name.split()[0]
        if first in QUESTION_WORDS:
            name = " ".join(name.split()[1:])
        name = _clean_candidate(name)
        if not name:
            continue
        if _is_temporal_context(question, name):
            continue
        if len(name.split()) == 1 and name in GENERIC_SINGLE_ENTITY_WORDS:
            continue
        key = normalize_entity(name)
        if key in seen or key in FACT_TERMS:
            continue
        seen.add(key)
        entities.append(Entity(name=name))
    return entities


def _validate_document(entities, document):
    for entity in entities:
        if _contains_entity_in_text(_heading_text(document.text), entity.name):
            return EntityMatchResult(
                evidence_id=document.id,
                requested_entity=entity.name,
                evidence_entity=entity.name,
                entity_match="exact_match",
                usable_for_direct_claim=True,
                reason="Exact entity match in heading.",
            )
        if _contains_entity_in_text(document.text, entity.name):
            return EntityMatchResult(
                evidence_id=document.id,
                requested_entity=entity.name,
                evidence_entity=entity.name,
                entity_match="exact_match",
                usable_for_direct_claim=True,
                reason="Exact entity match in evidence text.",
            )
        if _contains_entity_in_source(document.source_doc, entity.name):
            return EntityMatchResult(
                evidence_id=document.id,
                requested_entity=entity.name,
                evidence_entity=entity.name,
                entity_match="exact_match",
                usable_for_direct_claim=True,
                reason="Exact entity match in source path.",
            )
        for alias in entity.aliases:
            if _contains_entity_in_source(document.source_doc, alias) or _contains_entity_in_text(document.text, alias):
                return EntityMatchResult(
                    evidence_id=document.id,
                    requested_entity=entity.name,
                    evidence_entity=alias,
                    entity_match="alias_match",
                    usable_for_direct_claim=True,
                    reason="Known alias match.",
                )

    evidence_entity = _first_named_entity(document.source_doc, document.text)
    if evidence_entity:
        requested_tokens = set(normalize_entity(entities[0].name).split())
        evidence_tokens = set(normalize_entity(evidence_entity).split())
        match_type = "related_entity" if requested_tokens & evidence_tokens else "mismatch"
        return EntityMatchResult(
            evidence_id=document.id,
            requested_entity=entities[0].name,
            evidence_entity=evidence_entity,
            entity_match=match_type,
            usable_for_direct_claim=False,
            reason="Evidence names a different entity.",
        )

    return EntityMatchResult(
        evidence_id=document.id,
        requested_entity=entities[0].name,
        entity_match="ambiguous",
        usable_for_direct_claim=False,
        reason="No exact entity signal found.",
    )


def annotate_documents(documents, matches):
    for document in documents:
        match = matches.get(document.id)
        if match is not None:
            setattr(document, "entity_match", match)
    return documents


def boost_entity_matches(results, entities):
    if not entities:
        return results

    boosted = []
    for result in results:
        boost = _entity_boost(result, entities)
        boosted.append(
            type(result)(
                id=result.id,
                text=result.text,
                source_doc=result.source_doc,
                chunk_index=result.chunk_index,
                score=result.score + boost,
            )
        )
    return sorted(boosted, key=lambda result: result.score, reverse=True)


def normalize_entity(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _entity_boost(result, entities):
    boost = 0.0
    for entity in entities:
        if _contains_entity_in_source(result.source_doc, entity.name):
            boost += 2.0
        if _contains_entity_in_text(_heading_text(result.text), entity.name):
            boost += 1.5
        if _contains_entity_in_text(result.text, entity.name):
            boost += 1.0
        for alias in entity.aliases:
            if _contains_entity_in_source(result.source_doc, alias) or _contains_entity_in_text(result.text, alias):
                boost += 0.8
    return boost


def _contains_entity_in_source(text, entity):
    entity_norm = normalize_entity(entity)
    if not entity_norm:
        return False
    path = Path(str(text).replace("\\", "/"))
    candidates = [path.stem, path.with_suffix("").as_posix()]
    return any(normalize_entity(candidate) == entity_norm for candidate in candidates)


def _contains_entity_in_text(text, entity):
    entity = str(entity).strip()
    if not entity:
        return False
    pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(entity)}(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(str(text)):
        tail = str(text)[match.end():]
        if re.match(r"\s+[A-Z][A-Za-z0-9]", tail):
            continue
        return True
    return False


def _contains_entity(text, entity):
    text_norm = normalize_entity(text)
    entity_norm = normalize_entity(entity)
    if not text_norm or not entity_norm:
        return False
    return re.search(rf"(?<!\w){re.escape(entity_norm)}(?!\w)", text_norm) is not None


def _extract_aliases(entities, documents):
    aliases = {entity.name: [] for entity in entities}
    patterns = [
        r"{name}\s*,?\s+also known as\s+([A-Z][A-Za-z0-9 ]+)",
        r"{name}\s*,?\s+called\s+([A-Z][A-Za-z0-9 ]+)",
        r"{name}\s*,?\s+also called\s+([A-Z][A-Za-z0-9 ]+)",
    ]
    for entity in entities:
        for document in documents:
            if not (
                _contains_entity_in_source(document.source_doc, entity.name)
                or _contains_entity_in_text(document.text, entity.name)
            ):
                continue
            for pattern in patterns:
                regex = pattern.format(name=re.escape(entity.name))
                for match in re.finditer(regex, document.text):
                    alias = _clean_candidate(match.group(1))
                    if alias and alias not in aliases[entity.name]:
                        aliases[entity.name].append(alias)
    return aliases


def _heading_text(text):
    headings = []
    for line in str(text).splitlines()[:8]:
        stripped = line.strip()
        if stripped.startswith("#") or stripped.isupper():
            headings.append(stripped)
    return "\n".join(headings)


def _first_named_entity(source_doc, text):
    source_stem = Path(str(source_doc).replace("\\", "/")).stem
    source_words = _title_from_slug(source_stem)
    if source_words:
        return source_words
    match = re.search(r"\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b", str(text))
    if match:
        return match.group(0)
    return ""


def _title_from_slug(value):
    words = [
        word
        for word in re.split(r"[_\-\s]+", value)
        if word and word.lower() not in FACT_TERMS
    ]
    if not words:
        return ""
    return " ".join(word.capitalize() for word in words)


def _clean_candidate(value):
    value = re.sub(r"\s+", " ", str(value)).strip(" ?.,:;")
    value = re.sub(
        r"\b(?:actual|authoritative|exact|official|precise|real|true)\b",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    words = [
        word
        for word in value.split()
        if word.lower() not in FACT_TERMS
    ]
    return " ".join(words).strip()


def _is_temporal_context(question, name):
    escaped = re.escape(name)
    return bool(
        re.search(rf"\b(?:age|era|period)\s+of\s+{escaped}\b", question, flags=re.IGNORECASE)
        or re.search(rf"\b{escaped}\s+of\s+[A-Z][A-Za-z0-9]+\b", question)
    )


def _allows_related_entities(question):
    return bool(set(re.findall(r"\w+", question.lower())) & RELATION_TERMS)


def _requires_entity_consistency(question):
    terms = set(re.findall(r"\w+", question.lower()))
    return bool(terms & FACT_TERMS)
