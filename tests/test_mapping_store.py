from legal_anonymizer.mapping_store import (
    build_mapping_table,
    export_mapping_xlsx,
    load_mapping_table,
    save_mapping_table,
)
from legal_anonymizer.models import Entity


def test_build_mapping_table_reuses_placeholder_for_same_entity():
    entities = [
        Entity("PERSON", "张三", 0, 2),
        Entity("PERSON", "张三", 10, 12),
        Entity("COMPANY", "上海明德科技有限公司", 20, 30),
    ]

    table = build_mapping_table("合同.docx", entities)

    assert len(table.mappings) == 2
    assert table.mappings[0].placeholder == "[[COMPANY_001]]"
    assert table.mappings[1].placeholder == "[[PERSON_001]]"


def test_save_and_load_mapping_table(tmp_path):
    table = build_mapping_table("合同.docx", [Entity("PERSON", "张三", 0, 2)])
    path = save_mapping_table(tmp_path, table)

    loaded = load_mapping_table(path)

    assert loaded.source_name == "合同.docx"
    assert loaded.mappings[0].value == "张三"


def test_export_mapping_xlsx_has_original_and_anonymized_columns(tmp_path):
    table = build_mapping_table(
        "合同.docx",
        [
            Entity("PERSON", "张三", 0, 2),
            Entity("PERSON", "张律师", 10, 13),
        ],
    )

    path = export_mapping_xlsx(tmp_path, table)

    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    assert sheet["B1"].value == "原始内容"
    assert sheet["C1"].value == "脱敏后内容"
    assert sheet["E1"].value == "来源"
    assert sheet["B2"].value == "张三"
    assert sheet["C2"].value == "[[PERSON_001]]"
