from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskFinding:
    category: str
    value: str
    reason: str


SAFE_UPPERCASE_TERMS = {
    "ADOPTION",
    "AI",
    "AMENDED",
    "AND",
    "CEO",
    "CFO",
    "CNY",
    "COMPANY",
    "CONSENT",
    "CTO",
    "EXHIBIT",
    "FROM",
    "HOLDERS",
    "KEY",
    "MAY",
    "NOW",
    "PDF",
    "PRC",
    "RECITALS",
    "RMB",
    "SCHEDULE",
    "SPOUSE",
    "THE",
    "THIS",
    "TIME",
    "TO",
    "USD",
    "VOTING",
    "WHEREOF",
    "WITNESS",
}


RISK_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "EMAIL",
        "疑似邮箱仍未脱敏",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    ("PHONE", "疑似手机号仍未脱敏", re.compile(r"(?<!\d)(?:\+?\d{1,3}[-\s]?)?1[3-9]\d{9}(?!\d)")),
    (
        "ID",
        "疑似身份证号仍未脱敏",
        re.compile(
            r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])"
            r"(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)"
        ),
    ),
    (
        "COMPANY",
        "疑似英文公司/律所名称仍未脱敏",
        re.compile(
            r"\b[A-Z][A-Za-z0-9&.,'()\- ]{1,80}?"
            r"(?:Co\.?,?\s*Ltd\.?|Company Limited|Global Limited|Limited|Law Firm|LLP|LLC|PLC|Inc\.?|Corporation)"
            r"(?=\s|[（(]|$)"
        ),
    ),
    (
        "ADDRESS",
        "疑似英文地址仍未脱敏",
        re.compile(
            r"\b(?:Suite\s+\d+[A-Za-z]?,\s*)?"
            r"\d+[A-Za-z0-9\s&/.,#-]{0,90}?"
            r"(?:Road|Rd|Street|St|Avenue|Ave|Lane|Ln|Drive|Dr|Center|Centre|Tower|Floor|F)\b"
            r"[A-Za-z0-9\s&/.,#()\-]{0,90}?"
            r"(?:China|PRC|New Zealand|Shanghai|Beijing|Hastings)\b"
        ),
    ),
    ("PERSON", "疑似甲乙方姓名仍未脱敏", re.compile(r"(?:甲方|乙方|委托人|联系人)[：:\s]*[\u4e00-\u9fa5]{2,4}")),
    ("ADDRESS", "疑似签署城市仍未脱敏", re.compile(r"在[\u4e00-\u9fa5]{2,12}市签订")),
    ("COMPANY", "疑似英文简称仍未脱敏", re.compile(r"[“\"']\s*[A-Z]{2,8}\s*[”\"']")),
)


def scan_anonymized_text(text: str) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    for category, reason, pattern in RISK_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0).strip()
            if "[[" in value or not value:
                continue
            if category == "COMPANY" and _is_safe_uppercase_term(value):
                continue
            findings.append(RiskFinding(category=category, value=value, reason=reason))
    return _dedupe_findings(findings)


def build_risk_report(findings: list[RiskFinding]) -> str:
    if not findings:
        return "自动漏扫结果: 通过，未发现高风险残留。\n"

    lines = [
        "自动漏扫结果: 未通过，文件已进入“需要复核-暂勿上传”。",
        "请不要上传该文件给 AI。",
        "",
        "高风险残留:",
    ]
    for finding in findings:
        lines.append(f"- {finding.category}: {finding.value} ({finding.reason})")
    lines.append("")
    lines.append("处理建议: 将上述内容加入规则或对照表后重新匿名化。")
    return "\n".join(lines) + "\n"


def _dedupe_findings(findings: list[RiskFinding]) -> list[RiskFinding]:
    seen: set[tuple[str, str]] = set()
    result: list[RiskFinding] = []
    for finding in findings:
        key = (finding.category, finding.value)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result


def _is_safe_uppercase_term(value: str) -> bool:
    normalized = value.strip().strip("\"'“”").upper()
    return normalized in SAFE_UPPERCASE_TERMS
