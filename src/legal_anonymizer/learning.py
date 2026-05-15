from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from legal_anonymizer.mapping_store import load_mapping_table
from legal_anonymizer.models import Entity, MappingTable

STATE_FILE = ".processing-state.json"


@dataclass(frozen=True)
class FileFingerprint:
    size: int
    modified_ns: int


def detect_learned_entities(text: str, mapping_dir: Path) -> list[Entity]:
    entities: list[Entity] = []
    for table in _iter_mapping_tables(mapping_dir):
        for mapping in table.mappings:
            value = mapping.value.strip()
            if len(value) < 2 or value.startswith("[["):
                continue
            start = 0
            while True:
                index = text.find(value, start)
                if index == -1:
                    break
                entities.append(
                    Entity(
                        category=mapping.category,
                        value=value,
                        start=index,
                        end=index + len(value),
                        confidence=0.99,
                        source="local_memory",
                    )
                )
                start = index + len(value)
    return entities


def was_processed(path: Path, state_dir: Path) -> bool:
    state = _load_state(state_dir)
    key = str(path.resolve())
    fingerprint = _fingerprint(path)
    return state.get(key) == asdict(fingerprint)


def mark_processed(path: Path, state_dir: Path) -> None:
    state = _load_state(state_dir)
    state[str(path.resolve())] = asdict(_fingerprint(path))
    _state_path(state_dir).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _iter_mapping_tables(mapping_dir: Path) -> list[MappingTable]:
    tables: list[MappingTable] = []
    for path in sorted(Path(mapping_dir).glob("*.mapping.json")):
        try:
            tables.append(load_mapping_table(path))
        except Exception:
            continue
    return tables


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
