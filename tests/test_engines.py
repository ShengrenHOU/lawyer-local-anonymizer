from legal_anonymizer.engines.pipeline import detect_entities_multi_engine


def test_multi_engine_merges_sources_for_same_value():
    text = "乙方：张三，身份证号：110101199001011234，邮箱：zhangsan@example.com。"

    entities = detect_entities_multi_engine(text)
    by_value = {entity.value: entity for entity in entities}

    assert by_value["张三"].source == "legal_rules"
    assert "presidio_light" in by_value["110101199001011234"].source
    assert "presidio_light" in by_value["zhangsan@example.com"].source


def test_multi_engine_detects_english_legal_surface():
    text = "FROM: Donnie Dong / Leif Ye\nRockit Global Limited\n22 Irongate Road East, Rd 5, Hastings, 4175, New Zealand"

    entities = detect_entities_multi_engine(text)
    values = {(entity.category, entity.value) for entity in entities}

    assert ("PERSON", "Donnie Dong") in values
    assert ("PERSON", "Leif Ye") in values
    assert ("COMPANY", "Rockit Global Limited") in values
    assert ("ADDRESS", "22 Irongate Road East, Rd 5, Hastings, 4175, New Zealand") in values

