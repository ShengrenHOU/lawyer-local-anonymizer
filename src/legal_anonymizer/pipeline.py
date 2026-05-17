from __future__ import annotations

from dataclasses import dataclass
import shutil
from pathlib import Path

from legal_anonymizer.anonymizer import anonymize_text
from legal_anonymizer.document_io import (
    anonymize_docx_document,
    read_text_document,
    restore_docx_document,
    scan_docx_unsupported_parts,
    write_text_document,
)
from legal_anonymizer.engines.pipeline import DetectionEngineError, detect_entities_multi_engine
from legal_anonymizer.history import record_history
from legal_anonymizer.learning import detect_learned_entities, filter_whitelisted_entities, learn_from_table
from legal_anonymizer.mapping_store import (
    build_mapping_table,
    export_mapping_xlsx,
    file_sha256,
    load_mapping_table,
    save_mapping_table,
    _safe_stem,
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
    review_required: bool = False


def anonymize_file(source_path: Path, workspace: WorkspacePaths) -> AnonymizedFileResult:
    text = read_text_document(source_path)
    structural_findings = _scan_source_structure(source_path)
    try:
        entities = detect_entities_multi_engine(text)
    except DetectionEngineError as exc:
        return _write_detection_failure_result(source_path, workspace, text, str(exc))
    entities.extend(detect_learned_entities(text, workspace.mappings))
    entities = filter_whitelisted_entities(entities, workspace.mappings)
    table = build_mapping_table(source_path.name, entities)
    table.source_sha256 = file_sha256(source_path)
    table.source_size = source_path.stat().st_size
    anonymized_text = anonymize_text(text, table)
    risk_findings = [*structural_findings, *scan_anonymized_text(anonymized_text)]
    upload_allowed = not risk_findings

    output_dir = workspace.anonymized if upload_allowed else workspace.review_required
    output_path = output_dir / _anonymized_output_name(source_path)
    report_path = workspace.mappings / f"{source_path.stem}.report.txt"
    risk_report_path = workspace.mappings / f"{source_path.stem}.risk-report.txt"
    task_summary_path = output_dir / f"{source_path.stem}.处理结果说明.txt"
    prompt_path = output_dir / f"{source_path.stem}.ai-prompt.txt"
    if source_path.suffix.lower() == ".docx":
        anonymize_docx_document(source_path, output_path, table)
        anonymized_text = read_text_document(output_path)
    else:
        write_text_document(output_path, anonymized_text)
    risk_findings = [*structural_findings, *scan_anonymized_text(anonymized_text)]
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
    table.anonymized_sha256 = file_sha256(output_path)
    mapping_path = save_mapping_table(workspace.mappings, table)
    mapping_xlsx_path = export_mapping_xlsx(workspace.mappings, table)
    learn_from_table(table, workspace.mappings)
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
    record_history(
        workspace.mappings,
        action="匿名化",
        source_name=source_path.name,
        output_path=output_path,
        status="可以上传 AI" if upload_allowed else "需要复核",
        item_count=len(table.mappings),
        risk_count=len(risk_findings),
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


def _scan_source_structure(source_path: Path) -> list[RiskFinding]:
    if source_path.suffix.lower() != ".docx":
        return []
    return [
        RiskFinding(
            category=finding.category,
            value=finding.part,
            reason=finding.reason,
        )
        for finding in scan_docx_unsupported_parts(source_path)
    ]


def restore_pasted_text(text: str, mapping_path: Path, workspace: WorkspacePaths) -> RestoredFileResult:
    table = load_mapping_table(mapping_path)
    restored = restore_text(text, table)
    review_required = bool(restored.unknown_placeholders or restored.missing_placeholders)
    output_dir = workspace.review_required if review_required else workspace.restored
    output_path = output_dir / f"{Path(table.source_name).stem}.restored.txt"
    write_text_document(output_path, restored.restored_text)
    record_history(
        workspace.mappings,
        action="还原",
        source_name=Path(table.source_name).name,
        output_path=output_path,
        status="需要复核" if review_required else "已还原",
        item_count=0,
        risk_count=len(restored.unknown_placeholders) + len(restored.missing_placeholders),
    )
    return RestoredFileResult(
        output_path=output_path,
        unknown_placeholders=restored.unknown_placeholders,
        missing_placeholders=restored.missing_placeholders,
        review_required=review_required,
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
    exact_path = workspace.mappings / f"{_safe_stem(source_path.stem)}.mapping.json"
    if exact_path.exists():
        return exact_path

    anonymized_stem = source_path.stem.replace(".anonymized", "")
    anonymized_path = workspace.mappings / f"{_safe_stem(anonymized_stem)}.mapping.json"
    if anonymized_path.exists():
        return anonymized_path

    candidates = sorted(
        workspace.mappings.glob("*.mapping.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    matched_candidates = [
        candidate
        for candidate in candidates
        if _mapping_source_matches(candidate, source_path)
    ]
    if len(matched_candidates) == 1:
        return matched_candidates[0]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError("找不到本文件对应的本地映射表，无法还原。")
    raise FileNotFoundError("存在多个映射表，请使用粘贴还原窗口手动选择对应映射表。")


def restore_file(source_path: Path, mapping_path: Path, workspace: WorkspacePaths) -> RestoredFileResult:
    text = read_text_document(source_path)
    table = load_mapping_table(mapping_path)
    restored = restore_text(text, table)
    review_required = bool(restored.unknown_placeholders or restored.missing_placeholders)
    output_dir = workspace.review_required if review_required else workspace.restored
    output_path = output_dir / _restored_output_name(source_path)
    if source_path.suffix.lower() == ".docx":
        restore_docx_document(source_path, output_path, table)
    else:
        write_text_document(output_path, restored.restored_text)
    record_history(
        workspace.mappings,
        action="还原",
        source_name=source_path.name,
        output_path=output_path,
        status="需要复核" if review_required else "已还原",
        item_count=0,
        risk_count=len(restored.unknown_placeholders) + len(restored.missing_placeholders),
    )
    return RestoredFileResult(
        output_path=output_path,
        unknown_placeholders=restored.unknown_placeholders,
        missing_placeholders=restored.missing_placeholders,
        review_required=review_required,
    )


def restore_file_auto(source_path: Path, workspace: WorkspacePaths) -> RestoredFileResult:
    mapping_path = resolve_mapping_path(source_path, workspace)
    return restore_file(source_path, mapping_path, workspace)


def _mapping_source_matches(mapping_path: Path, source_path: Path) -> bool:
    try:
        table = load_mapping_table(mapping_path)
    except (OSError, ValueError, KeyError):
        return False
    source_stem = source_path.stem.replace(".anonymized", "")
    table_stem = Path(table.source_name).stem
    try:
        source_hash = file_sha256(source_path)
    except OSError:
        source_hash = None
    if source_hash and source_hash in {table.source_sha256, table.anonymized_sha256}:
        return True
    return source_stem == table_stem or _safe_stem(source_stem) == _safe_stem(table_stem)


def _write_detection_failure_result(
    source_path: Path,
    workspace: WorkspacePaths,
    text: str,
    message: str,
) -> AnonymizedFileResult:
    output_path = workspace.review_required / f"{source_path.stem}.needs-review{source_path.suffix}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, output_path)
    table = build_mapping_table(source_path.name, [])
    table.source_sha256 = file_sha256(source_path)
    table.source_size = source_path.stat().st_size
    table.anonymized_sha256 = file_sha256(output_path)
    mapping_path = save_mapping_table(workspace.mappings, table)
    mapping_xlsx_path = export_mapping_xlsx(workspace.mappings, table)
    report_path = workspace.mappings / f"{source_path.stem}.report.txt"
    risk_report_path = workspace.mappings / f"{source_path.stem}.risk-report.txt"
    prompt_path = workspace.review_required / f"{source_path.stem}.ai-prompt.txt"
    task_summary_path = workspace.review_required / f"{source_path.stem}.处理结果说明.txt"
    risk_findings = [RiskFinding("SYSTEM", "detection_engine_failed", message)]
    report_path.write_text("识别失败：本文件未完成匿名化。\n", encoding="utf-8")
    risk_report_path.write_text(build_risk_report(risk_findings), encoding="utf-8")
    prompt_path.write_text("本文件未通过本地匿名化检测，请勿上传给 AI。\n", encoding="utf-8")
    task_summary_path.write_text(
        _build_task_summary(
            source_path=source_path,
            output_path=output_path,
            prompt_path=prompt_path,
            mapping_xlsx_path=mapping_xlsx_path,
            risk_report_path=risk_report_path,
            upload_allowed=False,
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
        anonymized_text=text,
        risk_findings=risk_findings,
        upload_allowed=False,
    )


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
