from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from legal_anonymizer.anonymizer import anonymize_text
from legal_anonymizer.document_io import (
    anonymize_docx_document,
    read_text_document,
    restore_docx_document,
    write_text_document,
)
from legal_anonymizer.engines.pipeline import detect_entities_multi_engine
from legal_anonymizer.learning import detect_learned_entities, learn_from_table
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
    task_summary_path: Path
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
    entities.extend(detect_learned_entities(text, workspace.mappings))
    table = build_mapping_table(source_path.name, entities)
    anonymized_text = anonymize_text(text, table)
    risk_findings = scan_anonymized_text(anonymized_text)
    upload_allowed = not risk_findings

    output_dir = workspace.anonymized if upload_allowed else workspace.review_required
    output_path = output_dir / _anonymized_output_name(source_path)
    report_path = workspace.mappings / f"{source_path.stem}.report.txt"
    risk_report_path = workspace.mappings / f"{source_path.stem}.risk-report.txt"
    task_summary_path = output_dir / f"{source_path.stem}.处理结果说明.txt"
    prompt_path = output_dir / f"{source_path.stem}.ai-prompt.txt"
    mapping_path = save_mapping_table(workspace.mappings, table)
    mapping_xlsx_path = export_mapping_xlsx(workspace.mappings, table)
    learn_from_table(table, workspace.mappings)

    if source_path.suffix.lower() == ".docx":
        anonymize_docx_document(source_path, output_path, table)
        anonymized_text = read_text_document(output_path)
    else:
        write_text_document(output_path, anonymized_text)
    risk_findings = scan_anonymized_text(anonymized_text)
    upload_allowed = not risk_findings
    if output_path.parent != (workspace.anonymized if upload_allowed else workspace.review_required):
        output_dir = workspace.anonymized if upload_allowed else workspace.review_required
        output_path = output_dir / _anonymized_output_name(source_path)
        prompt_path = output_dir / f"{source_path.stem}.ai-prompt.txt"
        task_summary_path = output_dir / f"{source_path.stem}.处理结果说明.txt"
        if source_path.suffix.lower() == ".docx":
            anonymize_docx_document(source_path, output_path, table)
        else:
            write_text_document(output_path, anonymized_text)
    report_path.write_text(build_report(table), encoding="utf-8")
    risk_report_path.write_text(build_risk_report(risk_findings), encoding="utf-8")
    prompt_path.write_text(build_ai_prompt(), encoding="utf-8")
    task_summary_path.write_text(
        _build_task_summary(
            source_path=source_path,
            output_path=output_path,
            prompt_path=prompt_path,
            mapping_xlsx_path=mapping_xlsx_path,
            risk_report_path=risk_report_path,
            upload_allowed=upload_allowed,
            risk_findings=risk_findings,
        ),
        encoding="utf-8",
    )

    return AnonymizedFileResult(
        output_path=output_path,
        mapping_path=mapping_path,
        mapping_xlsx_path=mapping_xlsx_path,
        report_path=report_path,
        prompt_path=prompt_path,
        risk_report_path=risk_report_path,
        task_summary_path=task_summary_path,
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
    output_path = workspace.restored / _restored_output_name(source_path)
    if source_path.suffix.lower() == ".docx":
        restore_docx_document(source_path, output_path, table)
    else:
        write_text_document(output_path, restored.restored_text)
    return RestoredFileResult(
        output_path=output_path,
        unknown_placeholders=restored.unknown_placeholders,
        missing_placeholders=restored.missing_placeholders,
    )


def restore_file_auto(source_path: Path, workspace: WorkspacePaths) -> RestoredFileResult:
    mapping_path = resolve_mapping_path(source_path, workspace)
    return restore_file(source_path, mapping_path, workspace)


def _build_task_summary(
    source_path: Path,
    output_path: Path,
    prompt_path: Path,
    mapping_xlsx_path: Path,
    risk_report_path: Path,
    upload_allowed: bool,
    risk_findings: list[RiskFinding],
) -> str:
    status = "可以上传 AI" if upload_allowed else "暂勿上传，需要复核"
    lines = [
        f"原文件: {source_path.name}",
        f"处理状态: {status}",
        "",
        "下一步:",
    ]
    if upload_allowed:
        lines.extend(
            [
                f"1. 只上传这个匿名文件给 AI: {output_path.name}",
                f"2. 可以同时复制这个提示词给 AI: {prompt_path.name}",
                "3. AI 处理后，把结果放入“03-AI结果文件-待还原”，或粘贴到程序窗口还原。",
            ]
        )
    else:
        lines.extend(
            [
                "1. 不要上传这个文件给 AI。",
                f"2. 先查看漏扫报告: {risk_report_path.name}",
                "3. 处理后重新把原文件放入“01-待匿名化”。",
            ]
        )
    lines.extend(
        [
            "",
            f"匿名文件: {output_path}",
            f"AI 提示词: {prompt_path}",
            f"本地对照表: {mapping_xlsx_path}",
            f"漏扫报告: {risk_report_path}",
            "",
            "注意: 不要把“99-本地映射表-不要上传”里的任何文件上传给 AI。",
        ]
    )
    if risk_findings:
        categories = sorted({finding.category for finding in risk_findings})
        lines.append(f"疑似风险类别: {', '.join(categories)}")
    return "\n".join(lines) + "\n"


def _anonymized_output_name(source_path: Path) -> str:
    if source_path.suffix.lower() == ".docx":
        return f"{source_path.stem}.anonymized.docx"
    return f"{source_path.stem}.anonymized.txt"


def _restored_output_name(source_path: Path) -> str:
    if source_path.suffix.lower() == ".docx":
        stem = source_path.stem.replace(".anonymized", "")
        return f"{stem}.restored.docx"
    return f"{source_path.stem}.restored.txt"
