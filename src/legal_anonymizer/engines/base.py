from __future__ import annotations

from typing import Protocol

from legal_anonymizer.models import Entity


class EntityEngine(Protocol):
    name: str

    def detect(self, text: str) -> list[Entity]:
        """Return detected sensitive entities."""


def merge_entities(entity_groups: list[list[Entity]]) -> list[Entity]:
    by_key: dict[tuple[str, str], Entity] = {}
    source_sets: dict[tuple[str, str], set[str]] = {}

    for entities in entity_groups:
        for entity in entities:
            value = entity.value.strip()
            if not value:
                continue
            key = (entity.category, value)
            source_sets.setdefault(key, set()).add(entity.source)
            existing = by_key.get(key)
            if existing is None or entity.confidence > existing.confidence:
                by_key[key] = Entity(
                    category=entity.category,
                    value=value,
                    start=entity.start,
                    end=entity.end,
                    confidence=entity.confidence,
                    source=entity.source,
                )

    merged: list[Entity] = []
    for key, entity in by_key.items():
        sources = "+".join(sorted(source_sets[key]))
        merged.append(
            Entity(
                category=entity.category,
                value=entity.value,
                start=entity.start,
                end=entity.end,
                confidence=entity.confidence,
                source=sources,
            )
        )
    return sorted(merged, key=lambda item: (-len(item.value), item.start, item.category))

