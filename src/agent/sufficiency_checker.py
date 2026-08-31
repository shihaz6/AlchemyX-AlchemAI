import json

from src.agent.prompts import build_sufficiency_prompt
from src.agent.schemas import SufficiencyResult


class SufficiencyChecker:

    def __init__(self, llm_client):

        self.llm_client = llm_client

    def check(self, question, documents):

        prompt = build_sufficiency_prompt(
            question,
            documents
        )

        response = self.llm_client.ask(prompt)

        return self._parse_response(response)

    def _parse_response(self, response):

        try:
            data = json.loads(response)

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