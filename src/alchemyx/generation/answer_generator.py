import json
import re
from dataclasses import dataclass

from ..agent.openrouter_client import OpenRouterClient

CLAIM_STOPWORDS = {
    "a",
    "about",
    "after",
    "also",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "could",
    "did",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "him",
    "his",
    "in",
    "is",
    "it",
    "its",
    "not",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "there",
    "this",
    "to",
    "was",
    "what",
    "when",
    "which",
    "who",
    "with",
}


@dataclass
class GeneratedAnswer:
    answer: str
    evidence_ids: list[str]


class AnswerGenerator:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or OpenRouterClient()

    def generate(self, question, documents, sufficiency_result=None):
        self.last_parse_error = False
        if not documents:
            return GeneratedAnswer(
                answer=(
                    "I could not find sufficient evidence in the indexed corpus "
                    "to answer that question."
                ),
                evidence_ids=[],
            )

        documents = _documents_for_generation(documents, sufficiency_result)
        prompt = build_answer_prompt(question, documents, sufficiency_result)
        try:
            response = self.llm_client.ask(prompt, purpose="final_generation")
        except TypeError:
            response = self.llm_client.ask(prompt)
        try:
            answer, evidence_ids = parse_answer_response(response, documents)
        except (json.JSONDecodeError, ValueError) as exc:
            from ..telemetry import log
            log(f"Final answer response ignored: {type(exc).__name__}")
            fallback = build_fallback_answer(question, documents, sufficiency_result)
            self.last_parse_error = True
            answer = fallback.answer
            evidence_ids = fallback.evidence_ids

        return GeneratedAnswer(
            answer=answer,
            evidence_ids=evidence_ids,
        )


def build_answer_prompt(question, documents, sufficiency_result=None):
    evidence_text = ""
    for document in documents:
        evidence_text += f"""
[EVIDENCE ID: {document.id}]
[SOURCE: {document.source_doc}, CHUNK: {document.chunk_index}]

{document.text}

"""

    sufficiency_text = ""
    if sufficiency_result is not None:
        sufficiency_text = f"""
SUFFICIENCY RESULT:
sufficient: {sufficiency_result.sufficient}
missing: {sufficiency_result.missing}
reason: {sufficiency_result.reason}
"""
        if getattr(sufficiency_result, "conflict_result", None) is not None:
            conflict_result = sufficiency_result.conflict_result
            sufficiency_text += f"""
CONFLICT ADJUDICATION:
has_conflict: {conflict_result.has_conflict}
candidate_values: {conflict_result.candidate_values}
resolved: {conflict_result.resolved}
selected_value: {conflict_result.selected_value}
authority_notes: {conflict_result.authority_notes}
reason: {conflict_result.reason}
"""

    return f"""
You are the final answer generator in a retrieval-augmented QA system.

Use only the supplied evidence. Do not invent facts. If the evidence is
incomplete, say what cannot be determined from the evidence.
If conflict adjudication resolved a contradiction, state the selected answer
directly, briefly mention the conflict if relevant, and explain why the selected
evidence was preferred. Do not say "cannot be determined" unless the supplied
evidence genuinely remains unresolved.

Every factual claim must cite the exact evidence ID that supports it. Use only
IDs that appear in SUPPLIED EVIDENCE. Do not guess chunk IDs. Do not cite an ID
unless the claim is directly supported by that evidence block.

QUESTION:
{question}

{sufficiency_text}
ALLOWED EVIDENCE IDS:
{", ".join(document.id for document in documents)}

SUPPLIED EVIDENCE:
{evidence_text}

Return ONLY valid JSON with exactly this shape:

{{
    "answer": "Final answer text with citations like [evidence_id].",
    "evidence_ids": ["IDs actually cited in the answer"]
}}
"""


def parse_answer_response(response, documents):
    allowed_ids = {document.id for document in documents}
    data = json.loads(_extract_json(response))

    if not isinstance(data, dict):
        raise ValueError("LLM answer response must be a JSON object")
    if not isinstance(data.get("answer"), str):
        raise ValueError("LLM answer response is missing string field: answer")
    if not isinstance(data.get("evidence_ids"), list):
        raise ValueError("LLM answer response is missing list field: evidence_ids")

    answer = data["answer"].strip()
    evidence_ids = _unique(data["evidence_ids"])
    invalid_ids = [evidence_id for evidence_id in evidence_ids if evidence_id not in allowed_ids]
    if invalid_ids:
        raise ValueError(f"LLM cited evidence IDs that were not supplied: {invalid_ids}")

    bracketed_ids = _bracketed_evidence_ids(answer)
    invalid_bracketed_ids = [
        evidence_id
        for evidence_id in bracketed_ids
        if evidence_id not in allowed_ids
    ]
    if invalid_bracketed_ids:
        raise ValueError(
            "LLM included unsupported citation IDs in the answer: "
            f"{invalid_bracketed_ids}"
        )

    missing_reported_ids = [
        evidence_id
        for evidence_id in bracketed_ids
        if evidence_id not in evidence_ids
    ]
    if missing_reported_ids:
        raise ValueError(
            "LLM answer cited IDs missing from evidence_ids: "
            f"{missing_reported_ids}"
        )
    validate_citation_support(answer, documents)

    return answer, evidence_ids


def build_fallback_answer(question, documents, sufficiency_result=None):
    evidence_ids = _fallback_evidence_ids(documents, sufficiency_result)
    selected_documents = [
        document
        for document in documents
        if document.id in evidence_ids
    ]
    if not selected_documents:
        selected_documents = documents[:2]
        evidence_ids = [document.id for document in selected_documents]

    if not selected_documents:
        return GeneratedAnswer(
            answer=(
                "I could not generate a final answer because no usable evidence "
                "was available."
            ),
            evidence_ids=[],
        )

    if sufficiency_result is not None and not sufficiency_result.sufficient:
        reason = "" if getattr(sufficiency_result, "parse_error", False) else sufficiency_result.reason
        answer = (
            "The evidence is not sufficient to answer the question definitively. "
            f"{reason}".strip()
        )
    else:
        answer = (
            "The final answer generator returned malformed output. The most "
            "relevant retrieved evidence is preserved below: "
            + " ".join(
                f"{_short_evidence_text(document.text)} [{document.id}]"
                for document in selected_documents[:2]
            )
        )

    return GeneratedAnswer(answer=answer, evidence_ids=evidence_ids)


def validate_citation_support(answer, documents):
    documents_by_id = {document.id: document for document in documents}
    unsupported = []

    for sentence in _answer_sentences(answer):
        cited_ids = _bracketed_evidence_ids(sentence)
        if not cited_ids:
            continue

        claim_tokens = _meaningful_tokens(re.sub(r"\[[^\]]+\]", "", sentence))
        if not claim_tokens:
            continue

        for evidence_id in cited_ids:
            document = documents_by_id.get(evidence_id)
            if document is None:
                continue
            evidence_tokens = _meaningful_tokens(document.text)
            overlap = claim_tokens & evidence_tokens
            if len(overlap) < 1:
                unsupported.append(evidence_id)

    if unsupported:
        raise ValueError(
            "LLM cited evidence IDs with weak lexical support: "
            f"{_unique(unsupported)}"
        )


def _documents_for_generation(documents, sufficiency_result):
    conflict_result = getattr(sufficiency_result, "conflict_result", None)
    if conflict_result is not None and conflict_result.has_conflict:
        allowed_ids = set(conflict_result.evidence_ids())
        selected_documents = [document for document in documents if document.id in allowed_ids]
        if selected_documents:
            return selected_documents
    if sufficiency_result is None or not sufficiency_result.evidence_ids:
        direct_documents = [
            document
            for document in documents
            if _usable_for_generation(document)
        ]
        return direct_documents

    documents_by_id = {document.id: document for document in documents}
    selected_documents = [
        documents_by_id[evidence_id]
        for evidence_id in sufficiency_result.evidence_ids
        if evidence_id in documents_by_id
    ]
    return selected_documents


def _usable_for_generation(document):
    entity_match = getattr(document, "entity_match", None)
    if entity_match is None:
        return True
    return (
        entity_match.usable_for_direct_claim
        or entity_match.entity_match in {"exact_match", "alias_match"}
    )


def _fallback_evidence_ids(documents, sufficiency_result):
    allowed_ids = {document.id for document in documents}
    ids = []
    if sufficiency_result is not None:
        ids.extend(
            evidence_id
            for evidence_id in sufficiency_result.evidence_ids
            if evidence_id in allowed_ids
        )
        conflict_result = getattr(sufficiency_result, "conflict_result", None)
        if conflict_result is not None:
            ids.extend(
                evidence_id
                for evidence_id in conflict_result.selected_evidence_ids
                if evidence_id in allowed_ids
            )
    return _unique(ids)


def _short_evidence_text(text, limit=220):
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _extract_json(response):
    if not isinstance(response, str):
        raise json.JSONDecodeError("response is not text", repr(response), 0)

    cleaned = response.strip()
    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced:
        return fenced.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start:end + 1]
    return cleaned


def _bracketed_evidence_ids(answer):
    return _unique(re.findall(r"\[([A-Za-z0-9_./ ·-]+_chunk\d+)\]", answer))


def _answer_sentences(answer):
    sentences = []
    consumed_end = 0
    for match in re.finditer(r"[^.!?]+[.!?](?:\s*\[[^\]]+\])*", answer):
        sentence = match.group(0).strip()
        if sentence:
            sentences.append(sentence)
        consumed_end = match.end()

    tail = answer[consumed_end:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def _meaningful_tokens(text):
    return {
        token
        for token in re.findall(r"\w+", text.lower())
        if len(token) > 2 and token not in CLAIM_STOPWORDS
    }


def _unique(values):
    unique_values = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or value in seen:
            continue

        unique_values.append(value)
        seen.add(value)
    return unique_values
