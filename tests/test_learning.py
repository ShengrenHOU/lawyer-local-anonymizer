from legal_anonymizer.learning import detect_learned_entities, mark_processed, was_processed
from legal_anonymizer.mapping_store import build_mapping_table, save_mapping_table
from legal_anonymizer.models import Entity


def test_learned_entities_reuse_previous_mapping(tmp_path):
    table = build_mapping_table("old.txt", [Entity("COMPANY", "Acme Holdings", 0, 13)])
    save_mapping_table(tmp_path, table)

    entities = detect_learned_entities("Acme Holdings signed again.", tmp_path)

    assert [(item.category, item.value, item.source) for item in entities] == [
        ("COMPANY", "Acme Holdings", "local_memory")
    ]


def test_processing_state_tracks_unchanged_file(tmp_path):
    source = tmp_path / "demo.txt"
    source.write_text("hello", encoding="utf-8")

    assert not was_processed(source, tmp_path)
    mark_processed(source, tmp_path)
    assert was_processed(source, tmp_path)

    source.write_text("changed", encoding="utf-8")
    assert not was_processed(source, tmp_path)
