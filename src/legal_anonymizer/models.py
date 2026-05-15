from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Entity:
    category: str
    value: str
    start: int
    end: int
    confidence: float = 1.0
    source: str = "legal_rules"


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
