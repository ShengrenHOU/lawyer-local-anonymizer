# Entity Recognition Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first recognition-quality slice: candidate entities, scoring, defined-term alias discovery, canonical alias grouping, and integration back into the existing mapping pipeline.

**Architecture:** Keep the current Python/PySide6 product and wrap the existing detector output into a candidate layer. The new layer scores candidates, resolves aliases, then emits final `Entity` objects for the current `MappingTable`, so document replacement, restore, UI, and packaging continue to work.

**Tech Stack:** Python 3.11+, dataclasses, pytest, existing `legal_anonymizer` package, no network calls, no local LLM, no C# rewrite.

---

## File Structure

- Modify `src/legal_anonymizer/models.py`: add `CandidateEntity`, `CanonicalEntity`, `ReplacementDecision`.
- Create `src/legal_anonymizer/recognition.py`: candidate adapter, defined-term detector, scorer, resolver, decision-to-entity conversion.
- Modify `src/legal_anonymizer/engines/pipeline.py`: call the new recognition layer after existing engines merge raw entities.
- Create `tests/test_recognition.py`: unit coverage for candidate adapter, scoring, alias detection, grouping, and replacement decisions.
- Modify `tests/test_engines.py`: add one pipeline-level English memo test so the existing anonymization path benefits from the new layer.

## Task 1: Core Recognition Models

**Files:**
- Modify: `src/legal_anonymizer/models.py`
- Test: `tests/test_recognition.py`

- [ ] **Step 1: Write failing model/adapter tests**

```python
from legal_anonymizer.models import Entity
from legal_anonymizer.recognition import candidates_from_entities


def test_candidates_from_entities_preserves_offsets_and_source():
    entity = Entity(category="COMPANY", value="Rockit Global Limited", start=10, end=31, source="legal_rules")

    candidates = candidates_from_entities("TO: Rockit Global Limited", [entity])

    assert candidates[0].text == "Rockit Global Limited"
    assert candidates[0].category == "COMPANY"
    assert candidates[0].start == 10
    assert candidates[0].end == 31
    assert candidates[0].source == "legal_rules"
```

- [ ] **Step 2: Run the failing test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_recognition.py::test_candidates_from_entities_preserves_offsets_and_source -q`

Expected: FAIL because `legal_anonymizer.recognition` does not exist.

- [ ] **Step 3: Implement models and adapter**

Add dataclasses in `models.py` and `candidates_from_entities()` in `recognition.py`.

- [ ] **Step 4: Run the test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_recognition.py::test_candidates_from_entities_preserves_offsets_and_source -q`

Expected: PASS.

## Task 2: Candidate Scoring

**Files:**
- Modify: `src/legal_anonymizer/recognition.py`
- Test: `tests/test_recognition.py`

- [ ] **Step 1: Write scoring tests**

```python
from legal_anonymizer.models import CandidateEntity
from legal_anonymizer.recognition import CandidateScorer


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
```

- [ ] **Step 2: Run scoring test and verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_recognition.py::test_scorer_replaces_high_risk_title_case_candidate -q`

Expected: FAIL until `CandidateScorer` exists.

- [ ] **Step 3: Implement `CandidateScorer`**

Use baseline scores from the spec and high-risk context bonuses.

- [ ] **Step 4: Run scoring tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_recognition.py -q`

Expected: PASS.

## Task 3: Defined-Term Alias Detector

**Files:**
- Modify: `src/legal_anonymizer/recognition.py`
- Test: `tests/test_recognition.py`

- [ ] **Step 1: Write alias detector tests**

```python
from legal_anonymizer.recognition import detect_defined_term_aliases


def test_defined_term_detector_finds_full_company_and_aliases():
    text = 'Rockit Trading (Shanghai) Co., Ltd. ("RTS", or the "Company")'

    candidates = detect_defined_term_aliases(text)
    values = {candidate.text for candidate in candidates}

    assert "Rockit Trading (Shanghai) Co., Ltd." in values
    assert "RTS" in values
```

- [ ] **Step 2: Run alias detector test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_recognition.py::test_defined_term_detector_finds_full_company_and_aliases -q`

Expected: FAIL until detector exists.

- [ ] **Step 3: Implement `detect_defined_term_aliases()`**

Detect English `Full Name ("ALIAS", or the "Company")` and Chinese short-name definitions. Exclude generic aliases such as `Company` unless they are explicitly marked as a defined alias.

- [ ] **Step 4: Run alias detector tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_recognition.py -q`

Expected: PASS.

## Task 4: Entity Resolution And Final Entity Conversion

**Files:**
- Modify: `src/legal_anonymizer/recognition.py`
- Test: `tests/test_recognition.py`

- [ ] **Step 1: Write resolver tests**

```python
from legal_anonymizer.recognition import detect_defined_term_aliases, resolve_candidates, entities_from_canonical


def test_resolver_groups_full_company_and_alias():
    text = 'Rockit Trading (Shanghai) Co., Ltd. ("RTS")'
    candidates = detect_defined_term_aliases(text)

    canonical = resolve_candidates(candidates)
    entities = entities_from_canonical(canonical)
    values = {entity.value for entity in entities}

    assert "Rockit Trading (Shanghai) Co., Ltd." in values
    assert "RTS" in values
```

- [ ] **Step 2: Run resolver test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_recognition.py::test_resolver_groups_full_company_and_alias -q`

Expected: FAIL until resolver exists.

- [ ] **Step 3: Implement resolver and entity conversion**

Group relation ids emitted by the defined-term detector. Convert each canonical surface form back into final `Entity` objects, keeping exact offsets.

- [ ] **Step 4: Run resolver tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_recognition.py -q`

Expected: PASS.

## Task 5: Pipeline Integration

**Files:**
- Modify: `src/legal_anonymizer/engines/pipeline.py`
- Test: `tests/test_engines.py`

- [ ] **Step 1: Write integration test**

```python
from legal_anonymizer.engines.pipeline import detect_entities_multi_engine


def test_pipeline_detects_defined_term_aliases_in_english_memo():
    text = 'TO: The Board of Directors of Rockit Trading (Shanghai) Co., Ltd. ("RTS")\nRE: Project Falcon'

    entities = detect_entities_multi_engine(text)
    values = {entity.value for entity in entities}

    assert "Rockit Trading (Shanghai) Co., Ltd." in values
    assert "RTS" in values
```

- [ ] **Step 2: Run integration test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_engines.py::test_pipeline_detects_defined_term_aliases_in_english_memo -q`

Expected: FAIL until pipeline calls recognition layer.

- [ ] **Step 3: Integrate recognition layer**

After `merge_entities(results)`, adapt raw entities to candidates, append defined-term candidates, score, resolve, convert to final entities, and merge/dedupe final entities.

- [ ] **Step 4: Run integration test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_engines.py::test_pipeline_detects_defined_term_aliases_in_english_memo -q`

Expected: PASS.

## Task 6: Verification And Commit

**Files:**
- No new implementation files unless test failures require focused fixes.

- [ ] **Step 1: Run unit and integration tests**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Run lint**

Run: `.\.venv\Scripts\python.exe -m ruff check src tests tools`

Expected: `All checks passed!`

- [ ] **Step 3: Run real Word smoke through source pipeline**

Run the existing real Word contract through `anonymize_file()` and confirm output folder, risk count, and placeholder count without printing sensitive content.

- [ ] **Step 4: Commit**

```powershell
git add src/legal_anonymizer/models.py src/legal_anonymizer/recognition.py src/legal_anonymizer/engines/pipeline.py tests/test_recognition.py tests/test_engines.py docs/superpowers/plans/2026-05-17-entity-recognition-framework.md
git commit -m "Implement entity recognition framework slice"
```

## Self-Review

- Spec coverage: covers first implementation slice from the design doc.
- Placeholder scan: no TBD/TODO placeholders.
- Scope: excludes C# rewrite, output filename changes, mapping encryption, local LLM, OCR, and UI changes.
- Type consistency: model and function names match the planned implementation.
