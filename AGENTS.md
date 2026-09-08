# AGENTS.md - Lawyer Local Anonymizer

## Scope and current implementation

This is a personal Windows desktop utility, not an ENYQUANT cloud service.
Read `C:/Users/73911/AGENTS.md` for personal defaults. Under the ENYQUANT
workspace follow its applicable safety/isolation rules, but do not import
company data ownership, develop branches or cloud workflows into this repo.

Current execution facts come from `pyproject.toml`, `src/legal_anonymizer/`,
tests and `docs/DEVELOPER_GUIDE.md`. The implementation is Python/PySide6.
`document_io.py` supports optional local Microsoft Word COM conversion of
legacy .doc files; do not launch Word or install it for a documentation task.
`config.py` owns actual folder names, formats and placeholder categories.

Before edits read the relevant existing developer, privacy and contribution
guidance. There is no PLAN_INDEX or progress/CURRENT; do not create generic
replacements. Read-only questions stay read-only: no app/watcher startup,
workspace initialization, sample processing, build or package installation
merely to explain the code.

## Product intent versus implemented protection

`docs/PRD.md`, `docs/IMPLEMENTATION.md` and `docs/CODEX_KICKOFF.md` retain the
original product/design intent. Their C#/WPF, no-Python, no-COM and phase-zero
startup directions are not instructions to rebuild the current app. Read them
when comparing requirements or planning an explicitly requested feature.
Do not treat an old checklist as current implementation or new task approval.

The encrypted-mapping requirement is UNIMPLEMENTED, not waived:
`mapping_store.py` writes readable JSON and Excel mapping tables. Neither
hashes, placeholders, the local-only design nor the upload-folder label
proves encryption or full PRD safety acceptance. Never claim this instruction
repair fixes encryption, guarantees anonymity or authorizes real-client use.
Report any additional requirement gap with source evidence; do not silently
weaken a gate, reinterpret an acceptance condition or implement an unrelated
security feature.

## Sensitive data and processing boundaries

- Keep originals read-only and client material outside Git, logs, screenshots
  and external services. Use synthetic fixtures for normal validation.
- Original, restored, review, mapping and local-memory files remain sensitive.
  Do not read real client samples or local mappings without exact task scope;
  do not upload them. Even anonymized outputs need human review before any
  separately authorized external use.
- Preserve fail-closed processing and the separate review folder. Missing or
  unknown restoration placeholders must not be silently treated as successful
  restoration. Optional absent spaCy models and core detector failures have
  different semantics; inspect existing code/tests before changing either.
- Preserve copied DOCX structure and source integrity. Do not claim every
  Word part, image or metadata case is supported from a README or passing unit
  test alone; inspect the exact IO/unsupported-part and risk checks.
- Do not add cloud APIs, upload behavior, telemetry, local LLMs or new
  dependencies unless the user explicitly scopes that change.

## Verification and delivery

Use existing pytest/ruff checks for implementation edits. Prose-only changes
need history preservation, paths, semantic consistency and discovery checks;
do not run the app or packaged client as a wording test. Full local suites
follow the workstation heavy-test admission rule. Keep existing CI unchanged.

This repo uses main. Work in an isolated documentation branch and preserve
existing work. Main PRs/pushes run CI tests/lint; v* tag pushes run Release.
Company develop merge delegation does not grant main/tag/release authority.
Do not publish a package, distribute client material or change release settings
under an instruction task. Report local adoption, PR/CI, main merge and
released-client behavior separately.
