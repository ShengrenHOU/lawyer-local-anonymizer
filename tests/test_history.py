from pathlib import Path

from legal_anonymizer.history import history_entries, record_history, render_history_report


def test_record_history_appends_latest_first(tmp_path):
    record_history(
        tmp_path,
        action="匿名化",
        source_name="contract.docx",
        output_path=Path("02-已匿名化-可上传AI/contract.anonymized.docx"),
        status="可以上传 AI",
        item_count=5,
        risk_count=0,
    )
    record_history(
        tmp_path,
        action="还原",
        source_name="ai-result.docx",
        output_path=Path("04-已还原/contract.restored.docx"),
        status="已还原",
        item_count=0,
        risk_count=0,
    )

    entries = history_entries(tmp_path)

    assert [entry["action"] for entry in entries] == ["还原", "匿名化"]
    assert entries[0]["source_name"] == "ai-result.docx"


def test_history_report_is_lawyer_readable(tmp_path):
    record_history(
        tmp_path,
        action="匿名化",
        source_name="contract.docx",
        output_path=Path("02-需要复核-暂勿上传/contract.anonymized.docx"),
        status="需要复核",
        item_count=3,
        risk_count=1,
    )

    report = render_history_report(tmp_path)

    assert "历史项目" in report
    assert "contract.docx" in report
    assert "需要复核" in report
    assert "风险 1 项" in report
