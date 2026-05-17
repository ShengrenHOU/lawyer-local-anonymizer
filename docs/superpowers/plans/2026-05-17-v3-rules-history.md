# V3 Rules and History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Absorb competitor lessons from the rules and history screens by adding local rule management and local project history without turning the app into a complex web workspace.

**Architecture:** Keep the folder-first PySide6 workflow. Extend `local-memory.json` into a user-visible rules source with enable/delete/export operations, and add a small append-only `local-history.json` file for anonymize/restore events. The GUI opens plain local reports instead of adding a large table-heavy interface.

**Tech Stack:** Python 3.11+, PySide6, pytest, ruff, current watcher/pipeline.

---

### Task 1: Rule Management API

**Files:**
- Modify: `tests/test_learning.py`
- Modify: `src/legal_anonymizer/learning.py`

- [ ] Add tests for disabling, enabling, deleting, and rendering local memory rules.
- [ ] Implement `set_memory_entry_enabled`, `delete_memory_entry`, and `render_memory_rules_report`.
- [ ] Verify with `python -m pytest tests/test_learning.py -q`.

### Task 2: Local History API

**Files:**
- Create: `src/legal_anonymizer/history.py`
- Create: `tests/test_history.py`

- [ ] Add tests for appending anonymize and restore history events.
- [ ] Implement `record_history`, `history_entries`, and `render_history_report`.
- [ ] Verify with `python -m pytest tests/test_history.py -q`.

### Task 3: Pipeline History Integration

**Files:**
- Modify: `tests/test_pipeline_text.py`
- Modify: `src/legal_anonymizer/pipeline.py`

- [ ] Add tests that anonymize and restore operations create history entries.
- [ ] Call `record_history` at successful anonymize and restore exit points.
- [ ] Verify with `python -m pytest tests/test_pipeline_text.py -q`.

### Task 4: GUI Entrypoints

**Files:**
- Modify: `src/legal_anonymizer/gui.py`

- [ ] Add `本地规则` and `历史项目` buttons.
- [ ] Generate readable local text reports and open them with the OS default app.
- [ ] Keep the main UI compact.

### Task 5: Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/USER_GUIDE.md`
- Modify: `LAWYER_USAGE.md`

- [ ] Document local rules and local history in lawyer-facing Chinese.
- [ ] Run `python -m pytest -q`.
- [ ] Run `ruff check src tests tools`.
- [ ] Run `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1`.
