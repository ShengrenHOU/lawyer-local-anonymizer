from __future__ import annotations

from legal_anonymizer.engines.base import merge_entities
from legal_anonymizer.engines.legal_rules import LegalRulesEngine
from legal_anonymizer.engines.ner_optional import OptionalSpacyNerEngine
from legal_anonymizer.engines.presidio_light import PresidioLightEngine
from legal_anonymizer.models import Entity
from legal_anonymizer.recognition import enhance_entities_with_recognition


class DetectionEngineError(RuntimeError):
    pass


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
            if isinstance(engine, OptionalSpacyNerEngine):
                results.append([])
                continue
            raise DetectionEngineError(f"{engine.name} failed during local detection.") from None
    raw_entities = merge_entities(results)
    return enhance_entities_with_recognition(text, raw_entities)
