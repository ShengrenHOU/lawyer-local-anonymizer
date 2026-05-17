# V3 Review Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add competitor-inspired local review controls: explicit "always anonymize" and "never anonymize" memory entries, plus a simpler lawyer-facing review panel.

**Architecture:** Keep the current folder-first PySide6 product. Extend the existing `local-memory.json` format with a `mode` field, then let the pipeline use memory in two places: blacklist entries add entities before replacement, whitelist entries remove matching entities before replacement. Keep mapping, Word replacement, restore, watcher, and release packaging unchanged.

**Tech Stack:** Python 3.11+, PySide6, pytest, ruff, existing docx pipeline.

---

### Task 1: Local Memory Behavior

**Files:**
- Modify: `tests/test_learning.py`
- Modify: `src/legal_anonymizer/learning.py`

- [ ] **Step 1: Add failing tests for blacklist and whitelist behavior**

Add tests proving that:
- a blacklist entry becomes an `Entity` with source `local_blacklist`
- a whitelist entry removes matching detector entities
- old memory entries without `mode` still behave as learned blacklist-like entries

- [ ] **Step 2: Run learning tests and verify failure**

Run: `python -m pytest tests/test_learning.py -q`

Expected: FAIL until new helpers exist.

- [ ] **Step 3: Implement memory modes**

Add:
- `add_memory_entry(mapping_dir, category, value, mode)`
- `filter_whitelisted_entities(entities, mapping_dir)`
- `memory_entries(mapping_dir)`

Normalize valid modes to `learned`, `blacklist`, and `whitelist`.

- [ ] **Step 4: Run learning tests and verify pass**

Run: `python -m pytest tests/test_learning.py -q`

Expected: PASS.

### Task 2: Pipeline Integration

**Files:**
- Modify: `tests/test_pipeline_text.py`
- Modify: `src/legal_anonymizer/pipeline.py`

- [ ] **Step 1: Add failing pipeline tests**

Add tests proving:
- a local blacklist entry anonymizes a phrase that default detectors do not know
- a local whitelist entry prevents anonymizing a known detected phrase

- [ ] **Step 2: Run pipeline tests and verify failure**

Run: `python -m pytest tests/test_pipeline_text.py -q`

Expected: FAIL until the pipeline filters/extends entities with memory modes.

- [ ] **Step 3: Integrate memory modes in `anonymize_file`**

Apply whitelist filtering after detector output and before mapping creation. Add blacklist/learned entities from memory before mapping creation.

- [ ] **Step 4: Run pipeline tests and verify pass**

Run: `python -m pytest tests/test_pipeline_text.py -q`

Expected: PASS.

### Task 3: Lawyer-Facing UI

**Files:**
- Modify: `src/legal_anonymizer/gui.py`

- [ ] **Step 1: Add a compact review/memory panel**

Add a small input field and buttons:
- `加入一定脱敏`
- `加入一定不脱敏`
- `打开需要复核`

Use simple Chinese copy, no technical terms like regex or NER.

- [ ] **Step 2: Wire buttons to local memory**

Call `add_memory_entry` with `mode="blacklist"` or `mode="whitelist"` and show a status message.

### Task 4: Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/USER_GUIDE.md`
- Modify: `LAWYER_USAGE.md`

- [ ] **Step 1: Document the new lawyer workflow**

Explain:
- `一定脱敏`: discovered missed client names, companies, project names
- `一定不脱敏`: generic legal words or phrases that should remain
- local memory is stored in `99-本地映射表-不要上传`

- [ ] **Step 2: Run verification**

Run:
- `python -m pytest -q`
- `ruff check src tests tools`
- `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1`

Expected: all pass and package build succeeds.
