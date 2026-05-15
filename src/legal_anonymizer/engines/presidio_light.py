from __future__ import annotations

import re

from legal_anonymizer.models import Entity


class PresidioLightEngine:
    """Lightweight Presidio-style recognizer layer without slow default NLP startup."""

    name = "presidio_light"

    PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
        ("PHONE", re.compile(r"(?<!\d)(?:\+?\d{1,3}[-\s]?)?(?:1[3-9]\d{9}|\d{3,4}[-\s]\d{6,8})(?!\d)")),
        (
            "ID",
            re.compile(
                r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])"
                r"(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)"
            ),
        ),
        ("BANK", re.compile(r"(?<!\d)\d{16,19}(?!\d)")),
        ("USCC", re.compile(r"\b[0-9A-Z]{18}\b")),
        ("CASE", re.compile(r"[（(]\d{4}[）)][\u4e00-\u9fa5A-Za-z0-9]+(?:民初|民终|执|刑初|行初)\d+号")),
        ("CONTRACT", re.compile(r"\b[A-Z]{1,12}-\d{4}-\d{3,12}\b")),
    )

    def detect(self, text: str) -> list[Entity]:
        entities: list[Entity] = []
        for category, pattern in self.PATTERNS:
            for match in pattern.finditer(text):
                entities.append(
                    Entity(
                        category=category,
                        value=match.group(0).strip(),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.92,
                        source=self.name,
                    )
                )
        return entities

