from pathlib import Path

from legal_anonymizer.anonymizer import anonymize_text
from legal_anonymizer.detectors import detect_entities
from legal_anonymizer.mapping_store import build_mapping_table


def test_detects_core_sensitive_entities():
    text = Path("tests/fixtures/sample_contract.txt").read_text(encoding="utf-8")

    entities = detect_entities(text)
    values = {(entity.category, entity.value) for entity in entities}

    assert ("COMPANY", "上海明德科技有限公司") in values
    assert ("PERSON", "张三") in values
    assert ("ID", "110101199001011234") in values
    assert ("PHONE", "13800000000") in values
    assert ("ADDRESS", "上海市浦东新区世纪大道100号") in values
    assert ("CONTRACT", "HT-2026-001") in values
    assert ("CASE", "（2026）沪0101民初1234号") in values
    assert ("BANK", "6222020202020202020") in values
    assert ("EMAIL", "zhangsan@example.com") in values
    assert ("USCC", "91310000MA1K123456") in values


def test_entities_are_sorted_longest_first_for_safe_replacement():
    entities = detect_entities("上海明德科技有限公司与明德科技签约")

    assert entities[0].value == "上海明德科技有限公司"


def test_detects_english_legal_letter_header_entities():
    text = """PRIVILEGED AND CONFIDENTIAL

TO: The Board of Directors of Rockit Trading (Shanghai) Co., Ltd.
Email: legal@example.com
Rockit Global Limited ( “Rockit” or “RGL” )
Rockit Trading Company Limited ( “RTC” )
22 Irongate Road East, Rd 5, Hastings, 4175, New Zealand
Rockit Trading (Shanghai) Co. Ltd. ( “RTS” , or the “Company” )
Suite 3101, 138 Huaihai Zhong Road, Huangpu, Shanghai, PRC

FROM: Donnie Dong / Leif Ye
Email: donnie@example.com / leif@example.com
Hylands Law Firm (Shanghai Office) ( “We” or “Hylands” )
11 & 12/F Tower S1 Bund Finance Center, 600 Zhongshan NO. 2 Road (E), Shanghai, China
"""

    entities = detect_entities(text)
    values = {(entity.category, entity.value) for entity in entities}

    assert ("COMPANY", "Rockit Trading (Shanghai) Co., Ltd.") in values
    assert ("COMPANY", "Rockit Global Limited") in values
    assert ("COMPANY", "Rockit Trading Company Limited") in values
    assert ("COMPANY", "Rockit Trading (Shanghai) Co. Ltd.") in values
    assert ("COMPANY", "RGL") in values
    assert ("COMPANY", "RTC") in values
    assert ("COMPANY", "RTS") in values
    assert ("COMPANY", "Hylands Law Firm") in values
    assert ("PERSON", "Donnie Dong") in values
    assert ("PERSON", "Leif Ye") in values
    assert ("ADDRESS", "22 Irongate Road East, Rd 5, Hastings, 4175, New Zealand") in values
    assert ("ADDRESS", "Suite 3101, 138 Huaihai Zhong Road, Huangpu, Shanghai, PRC") in values
    assert (
        "ADDRESS",
        "11 & 12/F Tower S1 Bund Finance Center, 600 Zhongshan NO. 2 Road (E), Shanghai, China",
    ) in values

    table = build_mapping_table("letter.txt", entities)
    anonymized = anonymize_text(text, table)
    for leaked in [
        "Rockit Trading (Shanghai) Co., Ltd.",
        "Rockit Global Limited",
        "Rockit Trading Company Limited",
        "22 Irongate Road East",
        "Suite 3101",
        "Donnie Dong",
        "Leif Ye",
        "Hylands Law Firm",
        "Bund Finance Center",
    ]:
        assert leaked not in anonymized


def test_detects_chinese_party_name_and_city_signature():
    text = """关于《上海明德科技有限公司投资协议》之补充协议

本《上海明德科技有限公司投资协议之补充协议》由以下各方于2026年5月【】日在北京市签订：

甲方：侯胜任（以下简称“甲方”或“创始人”）
身份证号：110101199001011234
"""

    entities = detect_entities(text)
    values = {(entity.category, entity.value) for entity in entities}

    assert ("COMPANY", "上海明德科技有限公司") in values
    assert ("PERSON", "侯胜任") in values
    assert ("ADDRESS", "北京市") in values or ("ADDRESS", "北京市签订") in values
