from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from legal_anonymizer.models import Entity, MappingTable

STATE_FILE = ".processing-state.json"
MEMORY_FILE = "local-memory.json"


@dataclass(frozen=True)
class FileFingerprint:
    size: int
    modified_ns: int


def detect_learned_entities(text: str, mapping_dir: Path) -> list[Entity]:
    entities: list[Entity] = []
    for item in _load_memory(mapping_dir):
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
    for mapping in table.mappings:
        value = mapping.value.strip()
        if len(value) < 2 or value.startswith("[["):
            continue
        by_key[(mapping.category, value)] = {"category": mapping.category, "value": value}
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


def _load_memory(mapping_dir: Path) -> list[dict[str, str]]:
    path = _memory_path(mapping_dir)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    items: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        category = item.get("category")
        value = item.get("value")
        if isinstance(category, str) and isinstance(value, str):
            items.append({"category": category, "value": value})
    return items
