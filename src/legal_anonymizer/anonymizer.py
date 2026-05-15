from __future__ import annotations

from legal_anonymizer.models import MappingTable


def anonymize_text(text: str, table: MappingTable) -> str:
    result = text
    for mapping in sorted(table.mappings, key=lambda item: -len(item.value)):
        result = result.replace(mapping.value, mapping.placeholder)
    return result

