from __future__ import annotations

import json
from pathlib import Path

from legal_anonymizer.models import utc_timestamp

HISTORY_FILE = "local-history.json"
MAX_HISTORY_ENTRIES = 200


def record_history(
    mapping_dir: Path,
    *,
    action: str,
    source_name: str,
    output_path: Path,
    status: str,
    item_count: int,
    risk_count: int,
) -> Path:
    entries = _load_history(mapping_dir)
    entries.insert(
        0,
        {
            "created_at": utc_timestamp(),
            "action": action,
            "source_name": source_name,
            "output_path": str(output_path),
            "status": status,
            "item_count": int(item_count),
            "risk_count": int(risk_count),
        },
    )
    return _write_history(mapping_dir, entries[:MAX_HISTORY_ENTRIES])


def history_entries(mapping_dir: Path) -> list[dict[str, object]]:
    return _load_history(mapping_dir)


def render_history_report(mapping_dir: Path) -> str:
    entries = _load_history(mapping_dir)
    if not entries:
        return "历史项目\n\n当前没有历史记录。\n"

    lines = [
        "历史项目",
        "",
        "说明: 本文件只记录处理摘要，不保存原文内容。不要上传本文件夹给 AI。",
        "",
    ]
    for index, entry in enumerate(entries, start=1):
        risk_text = f"风险 {entry.get('risk_count', 0)} 项"
        item_text = f"脱敏 {entry.get('item_count', 0)} 项"
        lines.append(
            f"{index}. {entry.get('created_at', '')} | {entry.get('action', '')} | "
            f"{entry.get('status', '')} | {entry.get('source_name', '')}"
        )
        lines.append(f"   输出: {entry.get('output_path', '')}")
        lines.append(f"   统计: {item_text}，{risk_text}")
        lines.append("")
    return "\n".join(lines)


def _history_path(mapping_dir: Path) -> Path:
    mapping_dir.mkdir(parents=True, exist_ok=True)
    return mapping_dir / HISTORY_FILE


def _load_history(mapping_dir: Path) -> list[dict[str, object]]:
    path = _history_path(mapping_dir)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    entries: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        entries.append(
            {
                "created_at": str(item.get("created_at", "")),
                "action": str(item.get("action", "")),
                "source_name": str(item.get("source_name", "")),
                "output_path": str(item.get("output_path", "")),
                "status": str(item.get("status", "")),
                "item_count": int(item.get("item_count", 0)),
                "risk_count": int(item.get("risk_count", 0)),
            }
        )
    return entries


def _write_history(mapping_dir: Path, entries: list[dict[str, object]]) -> Path:
    path = _history_path(mapping_dir)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
