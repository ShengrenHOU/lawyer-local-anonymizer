from legal_anonymizer.document_io import read_text_document, write_text_document
from legal_anonymizer.engines.presidio_light import PresidioLightEngine
from legal_anonymizer.history import history_entries
from legal_anonymizer.learning import add_memory_entry
from legal_anonymizer.mapping_store import build_mapping_table
from legal_anonymizer.models import Entity
from legal_anonymizer.pipeline import (
    anonymize_file,
    latest_mapping_path,
    latest_prompt_path,
    restore_file_auto,
    restore_pasted_text,
    restore_pasted_text_latest,
)
from legal_anonymizer.reporting import build_ai_prompt, build_report
from legal_anonymizer.workspace import create_workspace


def test_read_and_write_txt(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("乙方：张三", encoding="utf-8")

    assert read_text_document(source) == "乙方：张三"

    output = tmp_path / "output.txt"
    write_text_document(output, "已还原")

    assert output.read_text(encoding="utf-8") == "已还原"


def test_report_and_prompt_do_not_expose_raw_values():
    table = build_mapping_table("demo.docx", [Entity("PERSON", "张三", 0, 2)])

    report = build_report(table)
    prompt = build_ai_prompt()

    assert "PERSON: 1" in report
    assert "张三" not in report
    assert "不要修改、删除、合并或重命名任何 [[...]] 占位符" in prompt


def test_pipeline_anonymizes_and_restores_pasted_text(tmp_path):
    workspace = create_workspace(tmp_path)
    source = workspace.pending / "demo.txt"
    source.write_text("乙方：张三，手机号：13800000000。", encoding="utf-8")

    anonymized = anonymize_file(source, workspace)
    restored = restore_pasted_text(anonymized.anonymized_text, anonymized.mapping_path, workspace)

    assert anonymized.output_path.exists()
    assert anonymized.mapping_path.exists()
    assert anonymized.mapping_xlsx_path.exists()
    assert anonymized.report_path.exists()
    assert anonymized.prompt_path.exists()
    assert anonymized.task_summary_path.exists()
    assert "张三" not in anonymized.output_path.read_text(encoding="utf-8")
    assert "识别来源:" in anonymized.report_path.read_text(encoding="utf-8")
    assert "AI" in anonymized.task_summary_path.read_text(encoding="utf-8")
    assert restored.output_path.exists()
    assert restored.output_path.read_text(encoding="utf-8") == "乙方：张三，手机号：13800000000。"
    assert [entry["action"] for entry in history_entries(workspace.mappings)] == ["还原", "匿名化"]


def test_pipeline_auto_restores_downloaded_ai_file_when_single_mapping_exists(tmp_path):
    workspace = create_workspace(tmp_path)
    source = workspace.pending / "demo.txt"
    source.write_text("乙方：张三，手机号：13800000000。", encoding="utf-8")
    anonymized = anonymize_file(source, workspace)
    ai_result = workspace.restore_pending / "kimi-result.txt"
    ai_result.write_text(anonymized.anonymized_text, encoding="utf-8")

    restored = restore_file_auto(ai_result, workspace)

    assert restored.output_path.exists()
    assert restored.output_path.read_text(encoding="utf-8") == "乙方：张三，手机号：13800000000。"


def test_pipeline_auto_restores_matching_anonymized_file_when_multiple_mappings_exist(tmp_path):
    workspace = create_workspace(tmp_path)
    first = workspace.pending / "client agreement (v1).txt"
    second = workspace.pending / "other matter.txt"
    first.write_text("Party A: Alice Chen, phone: 13800000000.", encoding="utf-8")
    second.write_text("Party A: Bob Wang, phone: 13900000000.", encoding="utf-8")
    first_anonymized = anonymize_file(first, workspace)
    anonymize_file(second, workspace)

    restored = restore_file_auto(first_anonymized.output_path, workspace)

    assert restored.output_path.exists()
    assert restored.output_path.read_text(encoding="utf-8") == "Party A: Alice Chen, phone: 13800000000."


def test_pipeline_restores_pasted_text_with_latest_mapping(tmp_path):
    workspace = create_workspace(tmp_path)
    source = workspace.pending / "demo.txt"
    source.write_text("乙方：张三，手机号：13800000000。", encoding="utf-8")
    anonymized = anonymize_file(source, workspace)

    restored = restore_pasted_text_latest(anonymized.anonymized_text, workspace)

    assert latest_mapping_path(workspace) == anonymized.mapping_path
    assert latest_prompt_path(workspace) == anonymized.prompt_path
    assert restored.output_path.read_text(encoding="utf-8") == "乙方：张三，手机号：13800000000。"


def test_pipeline_quarantines_when_second_pass_finds_residual_risk(tmp_path):
    workspace = create_workspace(tmp_path)
    source = workspace.pending / "risky.txt"
    source.write_text("Please review Rockit Trading PLC tomorrow.", encoding="utf-8")

    anonymized = anonymize_file(source, workspace)

    assert not anonymized.upload_allowed
    assert anonymized.output_path.parent == workspace.review_required
    assert anonymized.risk_findings
    assert "暂勿上传" in anonymized.risk_report_path.read_text(encoding="utf-8")


def test_pipeline_anonymizes_local_blacklist_phrase(tmp_path):
    workspace = create_workspace(tmp_path)
    add_memory_entry(workspace.mappings, "PROJECT", "Project Falcon", "blacklist")
    source = workspace.pending / "memo.txt"
    source.write_text("Please review Project Falcon before signing.", encoding="utf-8")

    anonymized = anonymize_file(source, workspace)

    assert "Project Falcon" not in anonymized.anonymized_text
    assert "[[PROJECT_001]]" in anonymized.anonymized_text
    assert "local_blacklist" in anonymized.report_path.read_text(encoding="utf-8")


def test_pipeline_whitelist_keeps_matching_detected_phrase_out_of_mapping(tmp_path):
    workspace = create_workspace(tmp_path)
    add_memory_entry(workspace.mappings, "PHONE", "13800000000", "whitelist")
    source = workspace.pending / "memo.txt"
    source.write_text("Contact phone: 13800000000.", encoding="utf-8")

    anonymized = anonymize_file(source, workspace)

    assert "13800000000" in anonymized.anonymized_text
    assert "[[PHONE_001]]" not in anonymized.anonymized_text
    assert "13800000000" not in anonymized.mapping_path.read_text(encoding="utf-8")
    assert not anonymized.upload_allowed


def test_pipeline_quarantines_when_core_detection_engine_fails(tmp_path, monkeypatch):
    def fail_detect(self, text):
        raise RuntimeError("broken")

    monkeypatch.setattr(PresidioLightEngine, "detect", fail_detect)
    workspace = create_workspace(tmp_path)
    source = workspace.pending / "demo.txt"
    source.write_text("Party A: Alice Chen", encoding="utf-8")

    anonymized = anonymize_file(source, workspace)

    assert not anonymized.upload_allowed
    assert anonymized.output_path.parent == workspace.review_required
    assert "detection_engine_failed" in anonymized.risk_report_path.read_text(encoding="utf-8")


def test_restore_with_missing_placeholder_goes_to_review_required(tmp_path):
    workspace = create_workspace(tmp_path)
    source = workspace.pending / "demo.txt"
    source.write_text("Party A: Alice Chen, phone: 13800000000.", encoding="utf-8")
    anonymized = anonymize_file(source, workspace)
    damaged_ai_result = anonymized.anonymized_text.replace("[[PHONE_001]]", "the phone")

    restored = restore_pasted_text(damaged_ai_result, anonymized.mapping_path, workspace)

    assert restored.review_required
    assert restored.missing_placeholders == ["[[PHONE_001]]"]
    assert restored.output_path.parent == workspace.review_required
