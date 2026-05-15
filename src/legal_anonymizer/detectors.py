from __future__ import annotations

import re

from legal_anonymizer.models import Entity


SINGLE_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?\d{1,3}[-\s]?)?1[3-9]\d{9}(?!\d)")),
    (
        "ID",
        re.compile(
            r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])"
            r"(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)"
        ),
    ),
    ("USCC", re.compile(r"\b[0-9A-Z]{18}\b")),
    ("BANK", re.compile(r"(?<!\d)\d{16,19}(?!\d)")),
    (
        "CASE",
        re.compile(r"[（(]\d{4}[）)][\u4e00-\u9fa5A-Za-z0-9]+(?:民初|民终|执|刑初|行初)\d+号"),
    ),
    ("CONTRACT", re.compile(r"(?:合同编号|编号为|编号[:：]?)\s*([A-Za-z]{1,12}-\d{4}-\d{3,12})")),
    (
        "COMPANY",
        re.compile(
            r"[\u4e00-\u9fa5A-Za-z0-9（）()·&.\-\s]{2,60}"
            r"(?:有限公司|股份有限公司|有限责任公司|律师事务所|人民法院|仲裁委员会|银行)"
        ),
    ),
    (
        "COMPANY",
        re.compile(
            r"\b[A-Z][A-Za-z0-9&.,'()\- ]{1,80}?"
            r"(?:Co\.?,?\s*Ltd\.?|Company Limited|Global Limited|Limited|Law Firm|LLP|LLC|Inc\.?|Corporation)"
            r"(?=\s|[（(]|$)"
        ),
    ),
    (
        "ADDRESS",
        re.compile(
            r"[\u4e00-\u9fa5]{2,20}(?:省|市)[\u4e00-\u9fa5]{1,20}(?:区|县|市)"
            r"[\u4e00-\u9fa5A-Za-z0-9号弄路街道大厦座室\-]{2,80}"
        ),
    ),
    (
        "ADDRESS",
        re.compile(
            r"\b(?:Suite\s+\d+[A-Za-z]?,\s*)?"
            r"\d+[A-Za-z0-9\s&/.,#-]{0,90}?"
            r"(?:Road|Rd|Street|St|Avenue|Ave|Lane|Ln|Drive|Dr|Center|Centre|Tower|Floor|F)\b"
            r"[A-Za-z0-9\s&/.,#()\-]{0,90}?"
            r"(?:China|PRC|New Zealand|Shanghai|Beijing|Hastings)\b"
        ),
    ),
    (
        "ADDRESS",
        re.compile(
            r"\b\d{1,6}[A-Za-z0-9\s&/.,#-]{0,90}?"
            r"(?:Road|Rd|Street|St|Avenue|Ave|Lane|Ln|Drive|Dr|Center|Centre|Tower|Floor|F)\b"
        ),
    ),
)

CONTEXT_CAPTURE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "PERSON",
        re.compile(
            r"(?:甲方代表|甲方|乙方|委托人|联系人|法定代表人|代理人|创始人)"
            r"[：:\s]*([\u4e00-\u9fa5]{2,4})"
        ),
    ),
    (
        "PERSON",
        re.compile(
            r"\b(?:FROM|From|TO|To)\s*:\s*"
            r"([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){0,2}(?:[ \t]*/[ \t]*[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){0,2})*)"
        ),
    ),
    (
        "COMPANY",
        re.compile(r"\bThe Board of Directors of\s+([A-Z][A-Za-z0-9&.,'()\- ]{2,90})"),
    ),
    ("ADDRESS", re.compile(r"在([\u4e00-\u9fa5]{2,12}市)签订")),
)


def detect_entities(text: str) -> list[Entity]:
    entities: list[Entity] = []
    entities.extend(_detect_single_value_patterns(text))
    entities.extend(_detect_context_patterns(text))
    entities.extend(_detect_quoted_aliases(text))
    entities.extend(_detect_standalone_address_lines(text))

    deduped = _dedupe_entities(entities)
    return sorted(deduped, key=lambda item: (-len(item.value), item.start, item.category))


def _detect_single_value_patterns(text: str) -> list[Entity]:
    entities: list[Entity] = []
    for category, pattern in SINGLE_VALUE_PATTERNS:
        for match in pattern.finditer(text):
            if category == "CONTRACT" and match.lastindex:
                start, end = match.span(1)
                value = match.group(1)
            else:
                start, end = match.span()
                value = match.group(0)
            entities.append(Entity(category=category, value=value.strip(), start=start, end=end))
    return entities


def _detect_context_patterns(text: str) -> list[Entity]:
    entities: list[Entity] = []
    for category, pattern in CONTEXT_CAPTURE_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span(1)
            value = match.group(1).strip()
            if category in {"ADDRESS"}:
                entities.append(Entity(category=category, value=value, start=start, end=end))
            elif category == "PERSON":
                for part in re.split(r"\s*/\s*", value):
                    part = part.strip()
                    if _looks_like_english_person(part) or _looks_like_chinese_person(part):
                        part_start = text.find(part, start, end)
                        entities.append(
                            Entity(category=category, value=part, start=part_start, end=part_start + len(part))
                        )
            else:
                entities.append(Entity(category=category, value=value, start=start, end=end))
    return entities


def _detect_quoted_aliases(text: str) -> list[Entity]:
    entities: list[Entity] = []
    pattern = re.compile(
        r"[（(]\s*(?:the\s+)?[“\"']([^“”\"'()（）]{2,30})[”\"']"
        r"(?:\s*,?\s*(?:or|或)(?:\s+the)?\s*[“\"']([^“”\"'()（）]{2,30})[”\"'])?"
        r"\s*[）)]"
    )
    for match in pattern.finditer(text):
        for group_index in (1, 2):
            value = match.group(group_index)
            if not value:
                continue
            value = value.strip()
            if value.lower() in {"we", "the company", "company"}:
                continue
            category = "COMPANY" if value.isupper() or len(value) > 4 else "PERSON"
            entities.append(
                Entity(
                    category=category,
                    value=value,
                    start=match.start(group_index),
                    end=match.end(group_index),
                )
            )
    return entities


def _detect_standalone_address_lines(text: str) -> list[Entity]:
    entities: list[Entity] = []
    for line_match in re.finditer(r"^.+$", text, flags=re.MULTILINE):
        line = line_match.group(0).strip()
        if len(line) < 10 or "[[" in line:
            continue
        if _looks_like_english_address(line):
            entities.append(
                Entity(
                    category="ADDRESS",
                    value=line,
                    start=line_match.start() + line_match.group(0).find(line),
                    end=line_match.start() + line_match.group(0).find(line) + len(line),
                )
            )
    return entities


def _looks_like_english_address(line: str) -> bool:
    has_number = bool(re.search(r"\d", line))
    has_road_word = bool(
        re.search(
            r"\b(?:Road|Rd|Street|St|Avenue|Ave|Lane|Ln|Drive|Dr|Center|Centre|Tower|Suite|Floor|F)\b",
            line,
        )
    )
    has_place = bool(re.search(r"\b(?:China|PRC|Shanghai|Beijing|New Zealand|Hastings|Huangpu)\b", line))
    return has_number and has_road_word and has_place


def _looks_like_english_person(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}", value))


def _looks_like_chinese_person(value: str) -> bool:
    return bool(re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", value))


def _dedupe_entities(entities: list[Entity]) -> list[Entity]:
    seen: set[tuple[str, str]] = set()
    result: list[Entity] = []
    for entity in sorted(entities, key=lambda item: (item.start, -len(item.value), item.category)):
        value = entity.value.strip()
        if not value:
            continue
        key = (entity.category, value)
        if key in seen:
            continue
        seen.add(key)
        result.append(Entity(entity.category, value, entity.start, entity.end, entity.confidence))
    return result
