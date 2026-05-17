from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from legal_anonymizer.models import Entity, MappingTable, utc_timestamp

STATE_FILE = ".processing-state.json"
MEMORY_FILE = "local-memory.json"
MEMORY_MODES = {"learned", "blacklist", "whitelist"}


@dataclass(frozen=True)
class FileFingerprint:
    size: int
    modified_ns: int


def detect_learned_entities(text: str, mapping_dir: Path) -> list[Entity]:
    entities: list[Entity] = []
    for item in _load_memory(mapping_dir):
        if item.get("enabled") is False:
            continue
        mode = str(item.get("mode", "learned"))
        if mode == "whitelist":
            continue
        value = item["value"].strip()
        if len(value) < 2 or value.startswith("[["):
            continue
        source = "local_blacklist" if mode == "blacklist" else "local_memory"
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
                    source=source,
                )
            )
            start = index + len(value)
    return entities


def filter_whitelisted_entities(entities: list[Entity], mapping_dir: Path) -> list[Entity]:
    whitelist_values = {
        item["value"].strip()
        for item in _load_memory(mapping_dir)
        if item.get("enabled") is not False and item.get("mode") == "whitelist" and item["value"].strip()
    }
    if not whitelist_values:
        return entities
    return [entity for entity in entities if entity.value.strip() not in whitelist_values]


def add_memory_entry(mapping_dir: Path, category: str, value: str, mode: str) -> Path:
    normalized_value = value.strip()
    normalized_category = category.strip().upper() or "CUSTOM"
    normalized_mode = mode.strip().lower()
    if normalized_mode not in MEMORY_MODES:
        raise ValueError(f"Unsupported memory mode: {mode}")
    if len(normalized_value) < 2:
        raise ValueError("Memory value must contain at least 2 characters")

    by_key = {
        (str(item.get("mode", "learned")), item["category"], item["value"]): item
        for item in _load_memory(mapping_dir)
    }
    now = utc_timestamp()
    key = (normalized_mode, normalized_category, normalized_value)
    item = by_key.get(key)
    if item is None:
        item = {
            "category": normalized_category,
            "value": normalized_value,
            "mode": normalized_mode,
            "enabled": True,
            "occurrences": 0,
            "source_names": [],
            "first_seen": now,
            "last_seen": now,
        }
    item["enabled"] = True
    item["occurrences"] = int(item.get("occurrences", 0)) + 1
    item["last_seen"] = now
    by_key[key] = item
    return _write_memory(mapping_dir, by_key.values())


def memory_entries(mapping_dir: Path) -> list[dict[str, object]]:
    return _load_memory(mapping_dir)


def set_memory_entry_enabled(mapping_dir: Path, mode: str, category: str, value: str, enabled: bool) -> bool:
    items = _load_memory(mapping_dir)
    changed = False
    target = _memory_key(mode, category, value)
    for item in items:
        if _memory_key(str(item.get("mode", "learned")), str(item["category"]), str(item["value"])) == target:
            item["enabled"] = enabled
            item["last_seen"] = utc_timestamp()
            changed = True
    if changed:
        _write_memory(mapping_dir, items)
    return changed


def delete_memory_entry(mapping_dir: Path, mode: str, category: str, value: str) -> bool:
    items = _load_memory(mapping_dir)
    target = _memory_key(mode, category, value)
    kept = [
        item
        for item in items
        if _memory_key(str(item.get("mode", "learned")), str(item["category"]), str(item["value"])) != target
    ]
    if len(kept) == len(items):
        return False
    _write_memory(mapping_dir, kept)
    return True


def render_memory_rules_report(mapping_dir: Path) -> str:
    items = _load_memory(mapping_dir)
    if not items:
        return "本地规则中心\n\n当前没有本地规则。\n"

    groups = {
        "blacklist": "一定脱敏",
        "whitelist": "一定不脱敏",
        "learned": "自动学习",
    }
    lines = [
        "本地规则中心",
        "",
        "说明: 本文件只用于本地查看，不要上传给 AI。",
        "",
    ]
    for mode, title in groups.items():
        group_items = [item for item in items if item.get("mode") == mode]
        lines.append(f"## {title}")
        if not group_items:
            lines.append("- 暂无")
        for index, item in enumerate(group_items, start=1):
            enabled = "启用" if item.get("enabled", True) else "停用"
            category = item["category"]
            value = item["value"]
            occurrences = item.get("occurrences", 0)
            lines.append(f"- {index}. [{enabled}] {category}: {value}（出现 {occurrences} 次）")
        lines.append("")
    return "\n".join(lines)


def learn_from_table(table: MappingTable, mapping_dir: Path) -> Path:
    by_key = {
        (str(item.get("mode", "learned")), item["category"], item["value"]): item
        for item in _load_memory(mapping_dir)
    }
    now = utc_timestamp()
    for mapping in table.mappings:
        value = mapping.value.strip()
        if len(value) < 2 or value.startswith("[["):
            continue
        key = ("learned", mapping.category, value)
        item = by_key.get(key)
        if item is None:
            item = {
                "category": mapping.category,
                "value": value,
                "mode": "learned",
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
        by_key[key] = item
    return _write_memory(mapping_dir, by_key.values())


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
            mode = item.get("mode", "learned")
            normalized["mode"] = mode if mode in MEMORY_MODES else "learned"
            normalized["enabled"] = item.get("enabled", True)
            normalized["occurrences"] = int(item.get("occurrences", 1))
            source_names = item.get("source_names", [])
            normalized["source_names"] = source_names if isinstance(source_names, list) else []
            normalized["first_seen"] = item.get("first_seen", "")
            normalized["last_seen"] = item.get("last_seen", "")
            items.append(normalized)
    return items


def _write_memory(mapping_dir: Path, items: object) -> Path:
    path = _memory_path(mapping_dir)
    sorted_items = sorted(
        list(items),
        key=lambda item: (str(item.get("mode", "learned")), item["category"], item["value"]),
    )
    path.write_text(json.dumps(sorted_items, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _memory_key(mode: str, category: str, value: str) -> tuple[str, str, str]:
    normalized_mode = mode.strip().lower()
    if normalized_mode not in MEMORY_MODES:
        normalized_mode = "learned"
    return normalized_mode, category.strip().upper(), value.strip()
