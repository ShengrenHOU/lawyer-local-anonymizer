from __future__ import annotations

import re

from legal_anonymizer.models import MappingTable, RestoreResult

PLACEHOLDER_PATTERN = re.compile(r"\[\[[A-Z]+_\d{3}\]\]")


def restore_text(text: str, table: MappingTable) -> RestoreResult:
    known = {mapping.placeholder: mapping.value for mapping in table.mappings}
    seen = sorted(set(PLACEHOLDER_PATTERN.findall(text)))
    unknown = [placeholder for placeholder in seen if placeholder not in known]
    restored = text
    for placeholder, value in known.items():
        restored = restored.replace(placeholder, value)
    missing = [placeholder for placeholder in known if placeholder not in text]
    return RestoreResult(
        restored_text=restored,
        missing_placeholders=missing,
        unknown_placeholders=unknown,
    )

