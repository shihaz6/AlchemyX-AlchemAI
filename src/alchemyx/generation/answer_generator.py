from dataclasses import dataclass

from ..agent.openrouter_client import OpenRouterClient


@dataclass
class GeneratedAnswer:
    answer: str
    evidence_ids: list[str]


class AnswerGenerator:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or OpenRouterClient()

    def generate(self, question, documents, sufficiency_result=None):
        prompt = build_answer_prompt(question, documents, sufficiency_result)
        answer = self.llm_client.ask(prompt)
        return GeneratedAnswer(
            answer=answer,
            evidence_ids=[document.id for document in documents],
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

    return f"""
You are the final answer generator in a retrieval-augmented QA system.

Use only the supplied evidence. Do not invent facts. If the evidence is
incomplete, say what cannot be determined from the evidence. Reference evidence
IDs in the answer when making claims.

QUESTION:
{question}

{sufficiency_text}
SUPPLIED EVIDENCE:
{evidence_text}

Return the final answer only.
"""
