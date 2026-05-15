from __future__ import annotations

from collections import Counter

from legal_anonymizer.models import MappingTable


def build_report(table: MappingTable) -> str:
    counts = Counter(mapping.category for mapping in table.mappings)
    lines = [
        f"原文件: {table.source_name}",
        f"处理时间: {table.created_at}",
        "替换统计:",
    ]
    for category in sorted(counts):
        lines.append(f"- {category}: {counts[category]}")
    sources = sorted({source for mapping in table.mappings for source in mapping.sources})
    if sources:
        lines.append("识别来源:")
        for source in sources:
            lines.append(f"- {source}")
    lines.append("提示: 本报告不包含真实敏感值。请人工复核匿名化文件后再上传 AI。")
    return "\n".join(lines) + "\n"


def build_ai_prompt() -> str:
    return (
        "请处理我上传的匿名化文件。文件中的 [[PERSON_001]]、[[COMPANY_001]]、"
        "[[ADDRESS_001]] 等占位符代表已在本地匿名化的信息。\n\n"
        "请严格遵守：\n"
        "1. 不要修改、删除、合并或重命名任何 [[...]] 占位符。\n"
        "2. 如果需要引用主体，请原样引用占位符。\n"
        "3. 输出结果中继续保留这些占位符。\n"
    )
