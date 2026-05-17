import json

from legal_anonymizer.learning import (
    add_memory_entry,
    clear_learning_memory,
    delete_memory_entry,
    detect_learned_entities,
    filter_whitelisted_entities,
    learn_from_table,
    learning_entry_count,
    memory_entries,
    mark_processed,
    render_memory_rules_report,
    set_memory_entry_enabled,
    was_processed,
)
from legal_anonymizer.mapping_store import build_mapping_table, save_mapping_table
from legal_anonymizer.models import Entity


def test_learned_entities_reuse_previous_mapping(tmp_path):
    table = build_mapping_table("old.txt", [Entity("COMPANY", "Acme Holdings", 0, 13)])
    save_mapping_table(tmp_path, table)
    learn_from_table(table, tmp_path)

    entities = detect_learned_entities("Acme Holdings signed again.", tmp_path)

    assert [(item.category, item.value, item.source) for item in entities] == [
        ("COMPANY", "Acme Holdings", "local_memory")
    ]
    memory = json.loads((tmp_path / "local-memory.json").read_text(encoding="utf-8"))
    assert memory[0]["enabled"] is True
    assert memory[0]["occurrences"] == 1
    assert memory[0]["source_names"] == ["old.txt"]


def test_disabled_learning_memory_is_not_reused(tmp_path):
    (tmp_path / "local-memory.json").write_text(
        json.dumps(
            [
                {
                    "category": "COMPANY",
                    "value": "Acme Holdings",
                    "enabled": False,
                    "occurrences": 3,
                    "source_names": ["old.txt"],
                }
            ]
        ),
        encoding="utf-8",
    )

    entities = detect_learned_entities("Acme Holdings signed again.", tmp_path)

    assert entities == []


def test_blacklist_memory_entry_is_reused_as_local_blacklist(tmp_path):
    add_memory_entry(tmp_path, "PROJECT", "Project Falcon", "blacklist")

    entities = detect_learned_entities("Please review Project Falcon.", tmp_path)

    assert [(item.category, item.value, item.source) for item in entities] == [
        ("PROJECT", "Project Falcon", "local_blacklist")
    ]
    assert memory_entries(tmp_path)[0]["mode"] == "blacklist"


def test_whitelist_memory_entry_removes_matching_entities(tmp_path):
    add_memory_entry(tmp_path, "COMPANY", "Ordinary Course", "whitelist")
    entities = [
        Entity("COMPANY", "Ordinary Course", 0, 15, source="legal_rules"),
        Entity("PERSON", "Alice Chen", 20, 30, source="legal_rules"),
    ]

    filtered = filter_whitelisted_entities(entities, tmp_path)

    assert [(item.category, item.value) for item in filtered] == [("PERSON", "Alice Chen")]


def test_memory_entry_can_be_disabled_and_enabled(tmp_path):
    add_memory_entry(tmp_path, "PROJECT", "Project Falcon", "blacklist")

    set_memory_entry_enabled(tmp_path, "blacklist", "PROJECT", "Project Falcon", False)
    assert detect_learned_entities("Project Falcon", tmp_path) == []

    set_memory_entry_enabled(tmp_path, "blacklist", "PROJECT", "Project Falcon", True)
    assert detect_learned_entities("Project Falcon", tmp_path)[0].source == "local_blacklist"


def test_memory_entry_can_be_deleted(tmp_path):
    add_memory_entry(tmp_path, "PROJECT", "Project Falcon", "blacklist")

    deleted = delete_memory_entry(tmp_path, "blacklist", "PROJECT", "Project Falcon")

    assert deleted
    assert memory_entries(tmp_path) == []


def test_memory_rules_report_is_lawyer_readable(tmp_path):
    add_memory_entry(tmp_path, "PROJECT", "Project Falcon", "blacklist")
    add_memory_entry(tmp_path, "CUSTOM", "Ordinary Course", "whitelist")

    report = render_memory_rules_report(tmp_path)

    assert "本地规则中心" in report
    assert "一定脱敏" in report
    assert "Project Falcon" in report
    assert "一定不脱敏" in report
    assert "Ordinary Course" in report


def test_legacy_learning_memory_without_mode_still_reuses_previous_mapping(tmp_path):
    (tmp_path / "local-memory.json").write_text(
        json.dumps(
            [
                {
                    "category": "COMPANY",
                    "value": "Legacy Holdings",
                    "enabled": True,
                    "occurrences": 2,
                    "source_names": ["old.txt"],
                }
            ]
        ),
        encoding="utf-8",
    )

    entities = detect_learned_entities("Legacy Holdings signed again.", tmp_path)

    assert [(item.category, item.value, item.source) for item in entities] == [
        ("COMPANY", "Legacy Holdings", "local_memory")
    ]


def test_learning_memory_can_be_cleared_without_deleting_mapping(tmp_path):
    table = build_mapping_table("old.txt", [Entity("COMPANY", "Acme Holdings", 0, 13)])
    mapping_path = save_mapping_table(tmp_path, table)
    learn_from_table(table, tmp_path)

    assert learning_entry_count(tmp_path) == 1
    assert clear_learning_memory(tmp_path) == 1
    assert learning_entry_count(tmp_path) == 0
    assert mapping_path.exists()


def test_processing_state_tracks_unchanged_file(tmp_path):
    source = tmp_path / "demo.txt"
    source.write_text("hello", encoding="utf-8")

    assert not was_processed(source, tmp_path)
    mark_processed(source, tmp_path)
    assert was_processed(source, tmp_path)

    source.write_text("changed", encoding="utf-8")
    assert not was_processed(source, tmp_path)
