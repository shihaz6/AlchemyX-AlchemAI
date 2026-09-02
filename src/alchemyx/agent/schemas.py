from dataclasses import dataclass, field


@dataclass
class Claim:
    subject: str
    predicate: str
    value: str | None
    claim_type: str = "direct"
    certainty: str = "unknown"
    evidence_id: str = ""
    source_family_id: str = ""
    references: list[str] = field(default_factory=list)


@dataclass
class ConflictResult:
    has_conflict: bool
    claim: str
    candidate_values: list[str] = field(default_factory=list)
    supporting_evidence_ids: dict[str, list[str]] = field(default_factory=dict)
    authority_notes: list[str] = field(default_factory=list)
    recommended_search_queries: list[str] = field(default_factory=list)
    resolvable: bool = False
    resolved: bool = False
    selected_value: str = ""
    selected_evidence_ids: list[str] = field(default_factory=list)
    reason: str = ""
    needs_more_search: bool = False
    claims: list[Claim] = field(default_factory=list)
    parse_error: bool = False
    internal_errors: list[dict] = field(default_factory=list)

    def evidence_ids(self):
        ids = []
        for evidence_id in self.selected_evidence_ids:
            if evidence_id not in ids:
                ids.append(evidence_id)
        for evidence_ids in self.supporting_evidence_ids.values():
            for evidence_id in evidence_ids:
                if evidence_id not in ids:
                    ids.append(evidence_id)
        return ids


@dataclass
class Entity:
    name: str
    type: str = "unknown"
    aliases: list[str] = field(default_factory=list)


@dataclass
class EntityMatchResult:
    evidence_id: str
    requested_entity: str
    evidence_entity: str = ""
    entity_match: str = "ambiguous"
    usable_for_direct_claim: bool = False
    reason: str = ""


@dataclass
class SufficiencyResult:
    sufficient: bool
    missing: list[str]
    search_queries: list[str]
    evidence_ids: list[str]
    reason: str
    conflict_result: ConflictResult | None = None
    parse_error: bool = False
    internal_errors: list[dict] = field(default_factory=list)
