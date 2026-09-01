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

QUESTION:
{question}

RETRIEVED EVIDENCE:
{evidence_text}

RULES:

1. Use ONLY the supplied evidence.
2. Do NOT use outside knowledge.
3. Relevant information is not necessarily sufficient information.
4. Determine what important information is required to answer the question.
5. Check whether the retrieved evidence contains that information.
6. Information may be distributed across multiple documents.
7. If an important part of the answer is unsupported, mark the evidence
   as insufficient.
8. If the evidence is insufficient, identify what information is missing.
9. Generate targeted search queries that could find the missing information.
10. If the evidence is sufficient, do not generate additional search queries.
11. If important evidence conflicts, mark the evidence as insufficient unless
    the conflict can be resolved from the supplied evidence.
12. Do not answer the user's question.

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
- Do not invent facts.
- Do not answer the question.
- Judge whether the evidence is enough to answer it.
"""

    return prompt
