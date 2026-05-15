from __future__ import annotations

import tempfile
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
    if suffix == ".doc":
        with tempfile.TemporaryDirectory(prefix="legal-anonymizer-doc-") as temp_dir:
            docx_path = Path(temp_dir) / f"{path.stem}.docx"
            _convert_doc_to_docx(path, docx_path)
            document = Document(str(docx_path))
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


def _convert_doc_to_docx(source: Path, target: Path) -> None:
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "当前文件是旧版 .doc 格式。请安装 Microsoft Word 后重试，"
            "或先用 Word/WPS 另存为 .docx 再放入待匿名化文件夹。"
        ) from exc

    pythoncom.CoInitialize()
    word = None
    document = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        document = word.Documents.Open(str(source.resolve()), ReadOnly=True)
        document.SaveAs2(str(target.resolve()), FileFormat=16)
    except Exception as exc:
        raise RuntimeError(
            "无法自动读取旧版 .doc 文件。请确认本机已安装 Microsoft Word，"
            "或先将文件另存为 .docx 后再处理。"
        ) from exc
    finally:
        if document is not None:
            document.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()
