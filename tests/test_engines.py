import pytest

from legal_anonymizer.engines.pipeline import DetectionEngineError, detect_entities_multi_engine
from legal_anonymizer.engines.presidio_light import PresidioLightEngine


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


def test_pipeline_detects_defined_term_aliases_in_english_memo():
    text = 'TO: The Board of Directors of Rockit Trading (Shanghai) Co., Ltd. ("RTS")\nRE: Project Falcon'

    entities = detect_entities_multi_engine(text)
    values = {entity.value for entity in entities}

    assert "Rockit Trading (Shanghai) Co., Ltd." in values
    assert "RTS" in values


def test_core_engine_failure_is_not_silent(monkeypatch):
    def fail_detect(self, text):
        raise RuntimeError("broken")

    monkeypatch.setattr(PresidioLightEngine, "detect", fail_detect)

    with pytest.raises(DetectionEngineError):
        detect_entities_multi_engine("Alice Chen")
