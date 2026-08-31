from dataclasses import dataclass


@dataclass
class SufficiencyResult:
    sufficient: bool
    missing: list[str]
    search_queries: list[str]
    evidence_ids: list[str]
    reason: str