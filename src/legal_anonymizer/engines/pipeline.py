from __future__ import annotations

from legal_anonymizer.engines.base import merge_entities
from legal_anonymizer.engines.legal_rules import LegalRulesEngine
from legal_anonymizer.engines.ner_optional import OptionalSpacyNerEngine
from legal_anonymizer.engines.presidio_light import PresidioLightEngine
from legal_anonymizer.models import Entity


def detect_entities_multi_engine(text: str) -> list[Entity]:
    engines = [
        PresidioLightEngine(),
        OptionalSpacyNerEngine(),
        LegalRulesEngine(),
    ]
    results: list[list[Entity]] = []
    for engine in engines:
        try:
            results.append(engine.detect(text))
        except Exception:
            results.append([])
    return merge_entities(results)

