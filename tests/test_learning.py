import json

from legal_anonymizer.learning import (
    clear_learning_memory,
    detect_learned_entities,
    learn_from_table,
    learning_entry_count,
    mark_processed,
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
