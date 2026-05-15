from __future__ import annotations

from pathlib import Path

import fitz
from docx import Document


def read_text_document(path: Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        document = Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    if suffix == ".pdf":
        with fitz.open(str(path)) as pdf:
            return "\n".join(page.get_text("text") for page in pdf)
    raise ValueError(f"Unsupported document type: {suffix}")


def write_text_document(path: Path, text: str) -> Path:
    path = Path(path)
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix in {".txt", ".md"}:
        path.write_text(text, encoding="utf-8")
        return path
    if suffix == ".docx":
        document = Document()
        for line in text.splitlines() or [""]:
            document.add_paragraph(line)
        document.save(str(path))
        return path
    raise ValueError(f"Unsupported output type: {suffix}")

