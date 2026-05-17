from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from collections.abc import Iterable


@dataclass(frozen=True)
class Entity:
    category: str
    value: str
    start: int
    end: int
    confidence: float = 1.0
    source: str = "legal_rules"


@dataclass(frozen=True)
class CandidateEntity:
    text: str
    category: str
    start: int
    end: int
    source: str
    score: float = 0.0
    is_high_risk_zone: bool = False
    evidence: str = ""
    relation_id: str | None = None
    surface_role: str = "FULL"


@dataclass(frozen=True)
class CanonicalEntity:
    entity_id: str
    category: str
    candidates: list[CandidateEntity] = field(default_factory=list)

    @property
    def surface_forms(self) -> list[str]:
        return _unique_preserve_order(candidate.text for candidate in self.candidates)

    @property
    def aliases(self) -> list[str]:
        return _unique_preserve_order(
            candidate.text for candidate in self.candidates if candidate.surface_role == "ALIAS"
        )


@dataclass(frozen=True)
class ReplacementDecision:
    candidate: CandidateEntity
    action: str
    reason: str


@dataclass(frozen=True)
class PlaceholderMapping:
    placeholder: str
    category: str
    value: str
    sources: list[str] = field(default_factory=list)


@dataclass
class MappingTable:
    source_name: str
    created_at: str
    mappings: list[PlaceholderMapping] = field(default_factory=list)
    source_sha256: str | None = None
    source_size: int | None = None
    anonymized_sha256: str | None = None


@dataclass(frozen=True)
class RestoreResult:
    restored_text: str
    missing_placeholders: list[str]
    unknown_placeholders: list[str]


def utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
