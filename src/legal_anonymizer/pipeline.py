from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from legal_anonymizer.anonymizer import anonymize_text
from legal_anonymizer.document_io import read_text_document, write_text_document
from legal_anonymizer.engines.pipeline import detect_entities_multi_engine
from legal_anonymizer.mapping_store import (
    build_mapping_table,
    export_mapping_xlsx,
    load_mapping_table,
    save_mapping_table,
)
from legal_anonymizer.reporting import build_ai_prompt, build_report
from legal_anonymizer.restore import restore_text
from legal_anonymizer.risk_scanner import RiskFinding, build_risk_report, scan_anonymized_text
from legal_anonymizer.workspace import WorkspacePaths


@dataclass(frozen=True)
class AnonymizedFileResult:
    output_path: Path
    mapping_path: Path
    mapping_xlsx_path: Path
    report_path: Path
    prompt_path: Path
    risk_report_path: Path
    anonymized_text: str
    risk_findings: list[RiskFinding]
    upload_allowed: bool


@dataclass(frozen=True)
class RestoredFileResult:
    output_path: Path
    unknown_placeholders: list[str]
    missing_placeholders: list[str]


def anonymize_file(source_path: Path, workspace: WorkspacePaths) -> AnonymizedFileResult:
    text = read_text_document(source_path)
    entities = detect_entities_multi_engine(text)
    table = build_mapping_table(source_path.name, entities)
    anonymized_text = anonymize_text(text, table)
    risk_findings = scan_anonymized_text(anonymized_text)
    upload_allowed = not risk_findings

    output_dir = workspace.anonymized if upload_allowed else workspace.review_required
    output_path = output_dir / f"{source_path.stem}.anonymized.txt"
    report_path = workspace.mappings / f"{source_path.stem}.report.txt"
    risk_report_path = workspace.mappings / f"{source_path.stem}.risk-report.txt"
    prompt_path = output_dir / f"{source_path.stem}.ai-prompt.txt"
    mapping_path = save_mapping_table(workspace.mappings, table)
    mapping_xlsx_path = export_mapping_xlsx(workspace.mappings, table)

    write_text_document(output_path, anonymized_text)
    report_path.write_text(build_report(table), encoding="utf-8")
    risk_report_path.write_text(build_risk_report(risk_findings), encoding="utf-8")
    prompt_path.write_text(build_ai_prompt(), encoding="utf-8")

    return AnonymizedFileResult(
        output_path=output_path,
        mapping_path=mapping_path,
        mapping_xlsx_path=mapping_xlsx_path,
        report_path=report_path,
        prompt_path=prompt_path,
        risk_report_path=risk_report_path,
        anonymized_text=anonymized_text,
        risk_findings=risk_findings,
        upload_allowed=upload_allowed,
    )


def restore_pasted_text(text: str, mapping_path: Path, workspace: WorkspacePaths) -> RestoredFileResult:
    table = load_mapping_table(mapping_path)
    restored = restore_text(text, table)
    output_path = workspace.restored / f"{Path(table.source_name).stem}.restored.txt"
    write_text_document(output_path, restored.restored_text)
    return RestoredFileResult(
        output_path=output_path,
        unknown_placeholders=restored.unknown_placeholders,
        missing_placeholders=restored.missing_placeholders,
    )


def latest_mapping_path(workspace: WorkspacePaths) -> Path:
    candidates = sorted(
        workspace.mappings.glob("*.mapping.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("还没有找到本地映射表。请先把客户文件放入“01-待匿名化”。")
    return candidates[0]


def latest_prompt_path(workspace: WorkspacePaths) -> Path:
    candidates = sorted(
        workspace.anonymized.glob("*.ai-prompt.txt"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("还没有找到 AI 提示词。请先完成一次匿名化。")
    return candidates[0]


def restore_pasted_text_latest(text: str, workspace: WorkspacePaths) -> RestoredFileResult:
    return restore_pasted_text(text, latest_mapping_path(workspace), workspace)


def resolve_mapping_path(source_path: Path, workspace: WorkspacePaths) -> Path:
    exact_path = workspace.mappings / f"{source_path.stem}.mapping.json"
    if exact_path.exists():
        return exact_path

    anonymized_stem = source_path.stem.replace(".anonymized", "")
    anonymized_path = workspace.mappings / f"{anonymized_stem}.mapping.json"
    if anonymized_path.exists():
        return anonymized_path

    candidates = sorted(
        workspace.mappings.glob("*.mapping.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError("找不到本文件对应的本地映射表，无法还原。")
    raise FileNotFoundError("存在多个映射表，请使用粘贴还原窗口手动选择对应映射表。")


def restore_file(source_path: Path, mapping_path: Path, workspace: WorkspacePaths) -> RestoredFileResult:
    text = read_text_document(source_path)
    table = load_mapping_table(mapping_path)
    restored = restore_text(text, table)
    output_path = workspace.restored / f"{source_path.stem}.restored.txt"
    write_text_document(output_path, restored.restored_text)
    return RestoredFileResult(
        output_path=output_path,
        unknown_placeholders=restored.unknown_placeholders,
        missing_placeholders=restored.missing_placeholders,
    )


def restore_file_auto(source_path: Path, workspace: WorkspacePaths) -> RestoredFileResult:
    mapping_path = resolve_mapping_path(source_path, workspace)
    return restore_file(source_path, mapping_path, workspace)
