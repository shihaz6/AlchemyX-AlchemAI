import json
import re
from time import perf_counter

from .prompts import build_sufficiency_prompt
from .schemas import SufficiencyResult


class SufficiencyChecker:

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def check(self, question, documents):

        prompt = build_sufficiency_prompt(
            question,
            documents
        )

        started = perf_counter()
        response = self.llm_client.ask(prompt)
        from ..telemetry import log
        log(f"Sufficiency check: {perf_counter() - started:.2f}s")

        return self._parse_response(response)

    def _parse_response(self, response):

        try:
            data = json.loads(self._extract_json(response))

        except json.JSONDecodeError:
            raise ValueError(
                f"LLM returned invalid JSON:\n{response}"
            )

        required_fields = [
            "sufficient",
            "missing",
            "search_queries",
            "evidence_ids",
            "reason"
        ]

        for field in required_fields:

            if field not in data:
                raise ValueError(
                    f"Missing field from LLM response: {field}"
                )

        if not isinstance(data["sufficient"], bool):
            raise ValueError(
                "'sufficient' must be true or false"
            )

        if not isinstance(data["missing"], list):
            raise ValueError(
                "'missing' must be a list"
            )

        if not isinstance(data["search_queries"], list):
            raise ValueError(
                "'search_queries' must be a list"
            )

        if not isinstance(data["evidence_ids"], list):
            raise ValueError(
                "'evidence_ids' must be a list"
            )

        if not isinstance(data["reason"], str):
            raise ValueError(
                "'reason' must be a string"
            )

        return SufficiencyResult(
            sufficient=data["sufficient"],
            missing=data["missing"],
            search_queries=data["search_queries"],
            evidence_ids=data["evidence_ids"],
            reason=data["reason"]
        )

    @staticmethod
    def _extract_json(response):
        """Accept JSON returned plainly or inside a Markdown code fence."""
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

        # Some providers add a short sentence around an otherwise valid JSON
        # object. Keep parsing strict enough to reject arbitrary prose.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return cleaned[start:end + 1]
        return cleaned
