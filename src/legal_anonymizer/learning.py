from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from legal_anonymizer.models import Entity, MappingTable, utc_timestamp

STATE_FILE = ".processing-state.json"
MEMORY_FILE = "local-memory.json"


@dataclass(frozen=True)
class FileFingerprint:
    size: int
    modified_ns: int


def detect_learned_entities(text: str, mapping_dir: Path) -> list[Entity]:
    entities: list[Entity] = []
    for item in _load_memory(mapping_dir):
        if item.get("enabled") is False:
            continue
        value = item["value"].strip()
        if len(value) < 2 or value.startswith("[["):
            continue
        start = 0
        while True:
            index = text.find(value, start)
            if index == -1:
                break
            entities.append(
                Entity(
                    category=item["category"],
                    value=value,
                    start=index,
                    end=index + len(value),
                    confidence=0.99,
                    source="local_memory",
                )
            )
            start = index + len(value)
    return entities


def learn_from_table(table: MappingTable, mapping_dir: Path) -> Path:
    by_key = {(item["category"], item["value"]): item for item in _load_memory(mapping_dir)}
    now = utc_timestamp()
    for mapping in table.mappings:
        value = mapping.value.strip()
        if len(value) < 2 or value.startswith("[["):
            continue
        item = by_key.get((mapping.category, value))
        if item is None:
            item = {
                "category": mapping.category,
                "value": value,
                "enabled": True,
                "occurrences": 0,
                "source_names": [],
                "first_seen": now,
                "last_seen": now,
            }
        item["enabled"] = item.get("enabled", True)
        item["occurrences"] = int(item.get("occurrences", 0)) + 1
        source_names = list(item.get("source_names", []))
        if table.source_name not in source_names:
            source_names.append(table.source_name)
        item["source_names"] = sorted(source_names)
        item["last_seen"] = now
        by_key[(mapping.category, value)] = item
    items = sorted(by_key.values(), key=lambda item: (item["category"], item["value"]))
    path = _memory_path(mapping_dir)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def clear_learning_memory(mapping_dir: Path) -> int:
    count = learning_entry_count(mapping_dir)
    path = _memory_path(mapping_dir)
    if path.exists():
        path.unlink()
    return count


def learning_entry_count(mapping_dir: Path) -> int:
    return len(_load_memory(mapping_dir))


def was_processed(path: Path, state_dir: Path) -> bool:
    state = _load_state(state_dir)
    key = str(path.resolve())
    fingerprint = _fingerprint(path)
    return state.get(key) == asdict(fingerprint)


def mark_processed(path: Path, state_dir: Path) -> None:
    state = _load_state(state_dir)
    state[str(path.resolve())] = asdict(_fingerprint(path))
    _state_path(state_dir).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _fingerprint(path: Path) -> FileFingerprint:
    stat = path.stat()
    return FileFingerprint(size=stat.st_size, modified_ns=stat.st_mtime_ns)


def _state_path(state_dir: Path) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / STATE_FILE


def _load_state(state_dir: Path) -> dict[str, dict[str, int]]:
    path = _state_path(state_dir)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _memory_path(mapping_dir: Path) -> Path:
    mapping_dir.mkdir(parents=True, exist_ok=True)
    return mapping_dir / MEMORY_FILE


def _load_memory(mapping_dir: Path) -> list[dict[str, object]]:
    path = _memory_path(mapping_dir)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    items: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        category = item.get("category")
        value = item.get("value")
        if isinstance(category, str) and isinstance(value, str):
            normalized = {"category": category, "value": value}
            normalized["enabled"] = item.get("enabled", True)
            normalized["occurrences"] = int(item.get("occurrences", 1))
            source_names = item.get("source_names", [])
            normalized["source_names"] = source_names if isinstance(source_names, list) else []
            normalized["first_seen"] = item.get("first_seen", "")
            normalized["last_seen"] = item.get("last_seen", "")
            items.append(normalized)
    return items
