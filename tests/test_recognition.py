from legal_anonymizer.models import CandidateEntity, Entity
from legal_anonymizer.recognition import (
    CandidateScorer,
    candidates_from_entities,
    decisions_from_candidates,
    detect_defined_term_aliases,
    entities_from_canonical,
    resolve_candidates,
)


def test_candidates_from_entities_preserves_offsets_and_source():
    entity = Entity(category="COMPANY", value="Rockit Global Limited", start=4, end=25, source="legal_rules")

    candidates = candidates_from_entities("TO: Rockit Global Limited", [entity])

    assert candidates[0].text == "Rockit Global Limited"
    assert candidates[0].category == "COMPANY"
    assert candidates[0].start == 4
    assert candidates[0].end == 25
    assert candidates[0].source == "legal_rules"
    assert candidates[0].is_high_risk_zone is True


def test_scorer_replaces_high_risk_title_case_candidate():
    candidate = CandidateEntity(
        text="Project Falcon",
        category="MATTER",
        start=4,
        end=18,
        source="title_case_proper_noun",
        score=55,
        is_high_risk_zone=True,
        evidence="RE line",
    )

    scored = CandidateScorer().score([candidate])

    assert scored[0].score >= 80


def test_defined_term_detector_finds_full_company_and_aliases():
    text = 'Rockit Trading (Shanghai) Co., Ltd. ("RTS", or the "Company")'

    candidates = detect_defined_term_aliases(text)
    values = {candidate.text for candidate in candidates}

    assert "Rockit Trading (Shanghai) Co., Ltd." in values
    assert "RTS" in values
    assert "Company" not in values


def test_resolver_groups_full_company_and_alias():
    text = 'Rockit Trading (Shanghai) Co., Ltd. ("RTS")'
    candidates = CandidateScorer().score(detect_defined_term_aliases(text))

    canonical = resolve_candidates(candidates)
    entities = entities_from_canonical(canonical)
    values = {entity.value for entity in entities}

    assert len(canonical) == 1
    assert "Rockit Trading (Shanghai) Co., Ltd." in values
    assert "RTS" in values
    assert {entity.category for entity in entities} == {"COMPANY"}


def test_replacement_decisions_review_borderline_high_risk_candidates():
    candidate = CandidateEntity(
        text="Blue River",
        category="MATTER",
        start=4,
        end=14,
        source="title_case_proper_noun",
        score=50,
        is_high_risk_zone=True,
        evidence="subject line",
    )

    decisions = decisions_from_candidates([candidate])

    assert decisions[0].action == "review"
