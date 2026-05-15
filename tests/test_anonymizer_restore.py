from legal_anonymizer.anonymizer import anonymize_text
from legal_anonymizer.detectors import detect_entities
from legal_anonymizer.mapping_store import build_mapping_table
from legal_anonymizer.restore import restore_text


def test_anonymize_and_restore_text_round_trip():
    text = "乙方：张三，手机号：13800000000。张三确认签署。"
    entities = detect_entities(text)
    table = build_mapping_table("demo.txt", entities)

    anonymized = anonymize_text(text, table)
    restored = restore_text(anonymized, table)

    assert "[[PERSON_001]]" in anonymized
    assert "[[PHONE_001]]" in anonymized
    assert "张三" not in anonymized
    assert restored.restored_text == text
    assert restored.unknown_placeholders == []


def test_restore_reports_unknown_placeholder():
    table = build_mapping_table("demo.txt", [])

    restored = restore_text("请联系 [[PERSON_999]]。", table)

    assert restored.unknown_placeholders == ["[[PERSON_999]]"]

