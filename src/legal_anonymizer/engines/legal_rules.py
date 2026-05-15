from __future__ import annotations

from legal_anonymizer.detectors import detect_entities
from legal_anonymizer.models import Entity


class LegalRulesEngine:
    name = "legal_rules"

    def detect(self, text: str) -> list[Entity]:
        return [
            Entity(entity.category, entity.value, entity.start, entity.end, entity.confidence, self.name)
            for entity in detect_entities(text)
        ]

