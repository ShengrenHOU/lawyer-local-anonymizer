from __future__ import annotations

from functools import lru_cache

from legal_anonymizer.models import Entity


class OptionalSpacyNerEngine:
    name = "spacy_ner"

    LABEL_MAP = {
        "PERSON": "PERSON",
        "ORG": "COMPANY",
        "GPE": "ADDRESS",
        "LOC": "ADDRESS",
        "FAC": "ADDRESS",
    }

    def detect(self, text: str) -> list[Entity]:
        nlp = _load_spacy_model()
        if nlp is None:
            return []
        doc = nlp(text)
        entities: list[Entity] = []
        for ent in doc.ents:
            category = self.LABEL_MAP.get(ent.label_)
            if not category:
                continue
            value = ent.text.strip()
            if len(value) < 2:
                continue
            entities.append(
                Entity(
                    category=category,
                    value=value,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.78,
                    source=self.name,
                )
            )
        return entities


@lru_cache(maxsize=1)
def _load_spacy_model():
    try:
        import spacy
    except Exception:
        return None

    for model_name in ("en_core_web_sm", "zh_core_web_sm"):
        try:
            return spacy.load(model_name)
        except Exception:
            continue
    return None

