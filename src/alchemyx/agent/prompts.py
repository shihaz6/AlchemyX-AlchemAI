def build_sufficiency_prompt(question, documents):

    evidence_text = ""

    for doc in documents:
        evidence_text += f"""
[EVIDENCE ID: {doc.id}]

{doc.text}

"""

    prompt = f"""
You are the Sufficiency Checker in an agentic document retrieval system.

Your task is NOT to answer the user's question.

Your task is to determine whether the retrieved evidence contains
enough reliable information to answer the question accurately.

ORIGINAL QUESTION:
{question}

RETRIEVED EVIDENCE:
{evidence_text}

RULES:

1. Use ONLY the supplied evidence.
2. Do NOT use outside knowledge.
3. The ORIGINAL QUESTION is immutable. Do not reinterpret, broaden, rewrite,
   replace, or expand it.
4. Evaluate ONLY the answer type and information directly requested by the
   ORIGINAL QUESTION. A who question needs an identity, a when question needs
   a time/date, a why question needs a reason, and a summarize question needs
   a summary. Do not require biography, plot, themes, motivation, context, or
   other information unless explicitly requested.
5. Relevant information is not necessarily sufficient information.
6. Check whether the retrieved evidence contains that information.
7. Information may be distributed across multiple documents.
8. If an important part of the answer is unsupported, mark the evidence
   as insufficient.
9. If the question contains an unresolved reference such as "the book", "he",
   "that treaty", or "the city", and the evidence does not identify its
   referent, mark the evidence insufficient and identify the referent as
   missing.
10. Never assume or invent an entity, title, or fact. Do not replace "the book" with a title that is not in the question or evidence.
11. Generate search queries ONLY for information directly required by the
    ORIGINAL QUESTION and missing from the evidence. Queries must not introduce
    unsupported entities or facts.
12. If the evidence is sufficient, do not generate additional search queries.
13. If important evidence conflicts, mark the evidence as insufficient unless
    the conflict can be resolved from the supplied evidence with a defensible
    evidence-based reason for preferring one answer.
14. Conflict detected is not enough to support a "cannot be determined" answer.
    If the question asks for the true, actual, precise, official, real, or
    otherwise authoritative value, unresolved contradictions are especially
    important and should trigger targeted follow-up queries.
15. If a source points to another record that could resolve the requested fact,
    such as a register, record, ledger, decree, transcript, archive, codex, or
    annal, generate a targeted query for that record before marking sufficient.
16. If the retrieved evidence directly establishes that the requested answer is
    genuinely unknown, unconfirmed, disputed, or not recorded by the corpus
    itself, that can be sufficient evidence for an uncertainty answer. Mark
    sufficient=true only when the evidence establishes genuine uncertainty, cite
    the evidence IDs, and do not generate more search queries.
17. Do not answer the user's question.

Return ONLY valid JSON.

The JSON must have exactly this structure:

{{
    "sufficient": true,
    "missing": [],
    "search_queries": [],
    "evidence_ids": [],
    "reason": ""
}}

If insufficient, use:

{{
    "sufficient": false,
    "missing": ["information that is missing"],
    "search_queries": ["targeted search query"],
    "evidence_ids": ["IDs of evidence used"],
    "reason": "Short explanation of why the evidence is insufficient."
}}

Remember:
- The ORIGINAL QUESTION is immutable and must be evaluated verbatim.
- Do not invent facts.
- A supported "cannot be determined" answer can be sufficient evidence only
  when the evidence establishes genuine corpus-level uncertainty, not merely
  because two retrieved sources disagree.
- Do not answer the question.
- Judge whether the evidence is enough to answer it.
"""

    return prompt
