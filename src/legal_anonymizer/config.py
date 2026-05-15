from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceFolders:
    pending: str = "01-待匿名化"
    anonymized: str = "02-已匿名化-可上传AI"
    review_required: str = "02-需要复核-暂勿上传"
    restore_pending: str = "03-AI结果文件-待还原"
    restored: str = "04-已还原"
    mappings: str = "99-本地映射表-不要上传"


FOLDERS = WorkspaceFolders()

INPUT_EXTENSIONS = {".doc", ".docx", ".pdf", ".txt", ".md"}
RESTORE_EXTENSIONS = {".docx", ".txt", ".md"}

PLACEHOLDER_PREFIXES = {
    "PERSON": "PERSON",
    "COMPANY": "COMPANY",
    "PHONE": "PHONE",
    "ID": "ID",
    "ADDRESS": "ADDRESS",
    "BANK": "BANK",
    "CASE": "CASE",
    "CONTRACT": "CONTRACT",
    "EMAIL": "EMAIL",
    "USCC": "USCC",
}
