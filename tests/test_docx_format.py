from docx import Document

from legal_anonymizer.document_io import read_text_document
from legal_anonymizer.pipeline import anonymize_file, restore_file_auto
from legal_anonymizer.workspace import create_workspace


def test_docx_anonymize_and_restore_preserves_word_container_format(tmp_path):
    workspace = create_workspace(tmp_path)
    source = workspace.pending / "demo.docx"
    document = Document()
    document.sections[0].header.paragraphs[0].text = "联系电话：13800000000"
    paragraph = document.add_paragraph()
    run = paragraph.add_run("乙方：张三")
    run.bold = True
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "上海测试科技有限公司"
    document.save(source)

    anonymized = anonymize_file(source, workspace)

    assert anonymized.output_path.suffix == ".docx"
    anonymized_doc = Document(anonymized.output_path)
    assert len(anonymized_doc.tables) == 1
    assert anonymized_doc.paragraphs[0].runs[0].bold is True
    anonymized_text = read_text_document(anonymized.output_path)
    assert "张三" not in anonymized_text
    assert "13800000000" not in anonymized_text
    assert "[[PERSON_001]]" in anonymized_text
    assert "[[PHONE_001]]" in anonymized_text

    restored = restore_file_auto(anonymized.output_path, workspace)

    assert restored.output_path.suffix == ".docx"
    restored_doc = Document(restored.output_path)
    assert len(restored_doc.tables) == 1
    assert restored_doc.paragraphs[0].runs[0].bold is True
    restored_text = read_text_document(restored.output_path)
    assert "张三" in restored_text
    assert "13800000000" in restored_text


def test_docx_anonymize_collapses_company_suffix_split_across_runs(tmp_path):
    workspace = create_workspace(tmp_path)
    source = workspace.pending / "split-company.docx"
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("Goodwish")
    paragraph.add_run(" International Limited")
    document.save(source)

    anonymized = anonymize_file(source, workspace)

    anonymized_text = read_text_document(anonymized.output_path)
    assert "International Limited" not in anonymized_text
    assert "[[COMPANY_" in anonymized_text
