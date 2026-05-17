from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace

from legal_anonymizer.models import CandidateEntity, CanonicalEntity, Entity, ReplacementDecision


SOURCE_BASE_SCORES = {
    "presidio_light": 100.0,
    "memory": 100.0,
    "memory_exact": 100.0,
    "company_suffix": 95.0,
    "defined_term_full": 95.0,
    "defined_term_alias": 90.0,
    "address_context": 90.0,
    "legal_context_line": 80.0,
    "uppercase_acronym": 70.0,
    "title_case_proper_noun": 55.0,
    "quoted_term": 55.0,
    "legal_rules": 80.0,
    "spacy": 70.0,
}

HIGH_RISK_LINE_PATTERN = re.compile(
    r"^\s*(?:TO|FROM|CC|BCC|ATTENTION|RE|SUBJECT|Client|Counsel|Director|Contact|Address|Party\s+[A-D])\s*:",
    re.IGNORECASE,
)
ENGLISH_DEFINED_TERM_PATTERN = re.compile(
    r"(?P<full>\b[A-Z][A-Za-z0-9&.,'()\- ]{2,120}?"
    r"(?:Co\.?,?\s*Ltd\.?|Company Limited|Global Limited|Limited|Law Firm|LLP|LLC|PLC|Inc\.?|Corporation)"
    r")\s*\(\s*(?P<aliases>[^)]{2,80})\s*\)"
)
CHINESE_DEFINED_TERM_PATTERN = re.compile(
    r"(?P<full>[\u4e00-\u9fa5A-Za-z0-9（）()·&.\-\s]{2,80}"
    r"(?:有限公司|股份有限公司|有限责任公司|合伙企业|律师事务所|基金|中心|委员会|银行))"
    r"[（(][^）)]*(?:简称|以下称|以下简称)[“\"']?(?P<alias>[^”\"'）)]{2,30})[”\"']?[^）)]*[）)]"
)
GENERIC_DEFINED_TERMS = {"the company", "company", "we", "us", "party", "parties"}


def candidates_from_entities(text: str, entities: list[Entity]) -> list[CandidateEntity]:
    return [
        CandidateEntity(
            text=entity.value,
            category=_normalize_category(entity.category),
            start=entity.start,
            end=entity.end,
            source=entity.source,
            score=entity.confidence * 100,
            is_high_risk_zone=_is_high_risk_position(text, entity.start),
            evidence=f"existing_entity:{entity.source}",
        )
        for entity in entities
        if entity.value.strip()
    ]


def detect_defined_term_aliases(text: str) -> list[CandidateEntity]:
    candidates: list[CandidateEntity] = []
    for match_index, match in enumerate(ENGLISH_DEFINED_TERM_PATTERN.finditer(text), start=1):
        relation_id = f"defined_term_{match_index}"
        full, full_start, full_end = _clean_english_full_name(
            match.group("full"),
            match.start("full"),
            match.end("full"),
        )
        candidates.append(
            CandidateEntity(
                text=full,
                category="COMPANY",
                start=full_start,
                end=full_end,
                source="defined_term_full",
                score=95,
                is_high_risk_zone=_is_high_risk_position(text, match.start("full")),
                evidence="english_defined_term_full",
                relation_id=relation_id,
                surface_role="FULL",
            )
        )
        for alias, start, end in _iter_english_aliases(match.group("aliases"), match.start("aliases")):
            category = "ORG_ALIAS" if _looks_like_alias(alias) else "MATTER"
            candidates.append(
                CandidateEntity(
                    text=alias,
                    category=category,
                    start=start,
                    end=end,
                    source="defined_term_alias",
                    score=90,
                    is_high_risk_zone=True,
                    evidence="english_defined_term_alias",
                    relation_id=relation_id,
                    surface_role="ALIAS",
                )
            )

    for match_index, match in enumerate(CHINESE_DEFINED_TERM_PATTERN.finditer(text), start=1):
        relation_id = f"zh_defined_term_{match_index}"
        full = match.group("full").strip()
        alias = match.group("alias").strip()
        candidates.extend(
            [
                CandidateEntity(
                    text=full,
                    category="COMPANY",
                    start=match.start("full"),
                    end=match.end("full"),
                    source="defined_term_full",
                    score=95,
                    is_high_risk_zone=_is_high_risk_position(text, match.start("full")),
                    evidence="chinese_defined_term_full",
                    relation_id=relation_id,
                    surface_role="FULL",
                ),
                CandidateEntity(
                    text=alias,
                    category="ORG_ALIAS",
                    start=match.start("alias"),
                    end=match.end("alias"),
                    source="defined_term_alias",
                    score=90,
                    is_high_risk_zone=True,
                    evidence="chinese_defined_term_alias",
                    relation_id=relation_id,
                    surface_role="ALIAS",
                ),
            ]
        )
    return _dedupe_candidates(candidates)


class CandidateScorer:
    def score(self, candidates: list[CandidateEntity]) -> list[CandidateEntity]:
        occurrence_counts = _normalized_occurrence_counts(candidates)
        scored: list[CandidateEntity] = []
        for candidate in candidates:
            score = max(candidate.score, _base_score(candidate))
            if candidate.is_high_risk_zone:
                score += 25
            if occurrence_counts[_normalize_surface(candidate.text)] >= 2:
                score += 10
            if candidate.source == "defined_term_alias":
                score = max(score, 90)
            scored.append(replace(candidate, score=min(score, 100)))
        return scored


def resolve_candidates(candidates: list[CandidateEntity]) -> list[CanonicalEntity]:
    replaceable = [candidate for candidate in candidates if _should_replace(candidate)]
    grouped: dict[str, list[CandidateEntity]] = defaultdict(list)
    standalone_index = 0
    for candidate in sorted(replaceable, key=lambda item: (item.relation_id or "", item.start, -len(item.text))):
        if candidate.relation_id:
            key = candidate.relation_id
        else:
            standalone_index += 1
            key = f"{candidate.category.lower()}_{standalone_index}_{_normalize_surface(candidate.text)}"
        grouped[key].append(candidate)

    canonical: list[CanonicalEntity] = []
    counters: dict[str, int] = defaultdict(int)
    for candidates_for_entity in grouped.values():
        category = _canonical_category(candidates_for_entity)
        counters[category] += 1
        canonical.append(
            CanonicalEntity(
                entity_id=f"{category}_{counters[category]:03d}",
                category=category,
                candidates=_dedupe_candidates(candidates_for_entity),
            )
        )
    return canonical


def decisions_from_candidates(candidates: list[CandidateEntity]) -> list[ReplacementDecision]:
    decisions: list[ReplacementDecision] = []
    for candidate in candidates:
        if _should_replace(candidate):
            decisions.append(ReplacementDecision(candidate=candidate, action="replace", reason="score_threshold"))
        elif candidate.is_high_risk_zone and candidate.score >= 45:
            decisions.append(ReplacementDecision(candidate=candidate, action="review", reason="high_risk_low_score"))
        else:
            decisions.append(ReplacementDecision(candidate=candidate, action="ignore", reason="below_threshold"))
    return decisions


def entities_from_canonical(canonical_entities: list[CanonicalEntity]) -> list[Entity]:
    entities: list[Entity] = []
    for canonical in canonical_entities:
        for candidate in canonical.candidates:
            entities.append(
                Entity(
                    category=canonical.category,
                    value=candidate.text,
                    start=candidate.start,
                    end=candidate.end,
                    confidence=min(candidate.score / 100, 1.0),
                    source=f"recognition:{candidate.source}",
                )
            )
    return _dedupe_entities(entities)


def enhance_entities_with_recognition(text: str, raw_entities: list[Entity]) -> list[Entity]:
    candidates = candidates_from_entities(text, raw_entities)
    candidates.extend(detect_defined_term_aliases(text))
    scored = CandidateScorer().score(_dedupe_candidates(candidates))
    canonical = resolve_candidates(scored)
    enhanced_entities = entities_from_canonical(canonical)
    return _dedupe_entities([*raw_entities, *enhanced_entities])


def _iter_english_aliases(alias_text: str, offset: int) -> list[tuple[str, int, int]]:
    aliases: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[“\"']([^“”\"']{2,30})[”\"']", alias_text):
        alias = match.group(1).strip()
        if _is_generic_defined_term(alias):
            continue
        aliases.append((alias, offset + match.start(1), offset + match.end(1)))
    return aliases


def _clean_english_full_name(value: str, start: int, end: int) -> tuple[str, int, int]:
    cleaned = value.strip()
    leading_trim = len(value) - len(value.lstrip())
    trailing_trim = len(value.rstrip(" \t(")) - len(value.rstrip())
    start += leading_trim
    end -= trailing_trim
    prefixes = [
        "The Board of Directors of ",
        "Board of Directors of ",
        "Directors of ",
    ]
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            start += len(prefix)
            break
    cleaned = cleaned.rstrip(" (")
    end = start + len(cleaned)
    return cleaned, start, end


def _is_high_risk_position(text: str, position: int) -> bool:
    if position <= 1500:
        return True
    line_start = text.rfind("\n", 0, position) + 1
    line_end = text.find("\n", position)
    if line_end == -1:
        line_end = len(text)
    return bool(HIGH_RISK_LINE_PATTERN.search(text[line_start:line_end]))


def _base_score(candidate: CandidateEntity) -> float:
    for source_part in candidate.source.split("+"):
        if source_part in SOURCE_BASE_SCORES:
            return SOURCE_BASE_SCORES[source_part]
    return SOURCE_BASE_SCORES.get(candidate.source, candidate.score)


def _should_replace(candidate: CandidateEntity) -> bool:
    return (
        candidate.score >= 75
        or (candidate.score >= 55 and candidate.is_high_risk_zone)
        or candidate.source == "defined_term_alias"
    )


def _canonical_category(candidates: list[CandidateEntity]) -> str:
    categories = {candidate.category for candidate in candidates}
    if "COMPANY" in categories or "ORG" in categories or "ORG_ALIAS" in categories:
        return "COMPANY"
    if "UNKNOWN_PROPER" in categories:
        return "UNKNOWN"
    return sorted(categories)[0]


def _normalize_category(category: str) -> str:
    if category == "ORG":
        return "COMPANY"
    return category


def _looks_like_alias(alias: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9&.-]{1,10}", alias)) or len(alias) <= 20


def _is_generic_defined_term(alias: str) -> bool:
    return alias.strip().lower() in GENERIC_DEFINED_TERMS


def _normalized_occurrence_counts(candidates: list[CandidateEntity]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        counts[_normalize_surface(candidate.text)] += 1
    return counts


def _normalize_surface(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _dedupe_candidates(candidates: list[CandidateEntity]) -> list[CandidateEntity]:
    seen: set[tuple[str, int, int, str]] = set()
    result: list[CandidateEntity] = []
    for candidate in sorted(candidates, key=lambda item: (item.start, -len(item.text), item.category, item.source)):
        value = candidate.text.strip()
        if not value:
            continue
        key = (value, candidate.start, candidate.end, candidate.source)
        if key in seen:
            continue
        seen.add(key)
        result.append(replace(candidate, text=value))
    return result


def _dedupe_entities(entities: list[Entity]) -> list[Entity]:
    by_key: dict[tuple[str, str], Entity] = {}
    for entity in sorted(entities, key=lambda item: (item.start, -len(item.value), item.category)):
        key = (entity.category, entity.value)
        existing = by_key.get(key)
        if existing is None or entity.confidence > existing.confidence:
            by_key[key] = entity
    return sorted(by_key.values(), key=lambda item: (-len(item.value), item.start, item.category))
