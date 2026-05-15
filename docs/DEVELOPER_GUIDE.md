# Developer Guide

## Project Layout

```text
src/legal_anonymizer/
  config.py          folder names and supported extensions
  workspace.py       workspace creation
  detectors.py       rule-based entity detection
  engines/           multi-engine detection pipeline
  learning.py        local learning memory and processed-file state
  risk_scanner.py    second-pass leakage gate
  mapping_store.py   JSON mapping and Excel comparison table
  anonymizer.py      text replacement
  restore.py         placeholder restore
  document_io.py     doc/docx/pdf/text IO plus docx in-place replacement helpers
  pipeline.py        high-level anonymize/restore flows
  watcher.py         folder watcher
  gui.py             PySide6 desktop UI
```

## Local Development

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check src tests
```

## Build

```powershell
.\scripts\build_windows.ps1
```

## Detection Pipeline

Production anonymization calls `detect_entities_multi_engine()`.

Detection layers:

- `PresidioLightEngine`: fast local recognizers for structured PII, without slow default NLP startup.
- `OptionalSpacyNerEngine`: lazy-loads `en_core_web_sm` or `zh_core_web_sm` if installed; otherwise returns no entities.
- `LegalRulesEngine`: legal-document-specific fallback patterns.

All entities are merged into a single case entity table. The mapping report and Excel comparison table include entity source labels so regressions can be traced.

`local-memory.json` is a separate local learning store under the mapping folder. It is intentionally separate from per-file mapping tables so a user can clear learning memory without breaking restoration for already processed files.

For `.docx`, anonymization and restoration modify a copied Word document directly instead of flattening to text. Replacement covers body paragraphs, tables, headers, and footers. The implementation replaces across Word text nodes while preserving unrelated run boundaries and styles.

Core detector failures are fail-closed: the file is routed to `02-需要复核-暂勿上传` instead of producing an uploadable result. Optional spaCy model absence remains a soft fallback.

The second-pass leakage gate is intentionally conservative. It blocks residual structured PII plus common legal-document residue such as Chinese company/institution names, Chinese party-name contexts, Chinese addresses, English company/law-firm names, English addresses, and quoted acronym aliases. This gate is not a replacement for first-pass anonymization; it is the last upload-safety barrier.

Restoration is also gated. If an AI result deletes a required placeholder or introduces an unknown placeholder, the restored output is written to the review folder and surfaced as requiring manual review.

## Release Checklist

1. Run tests and lint.
2. Build Windows distribution.
3. Start `dist\LegalAnonymizer\LegalAnonymizer.exe`.
4. Confirm the workspace folders are created.
5. Put a sample file into `01-待匿名化`.
6. Confirm `.docx` input creates anonymized `.docx`; confirm text/PDF input creates text output.
7. Confirm JSON mapping, Excel comparison table, report, risk report, prompt, and per-file result summary are generated.
8. Restore a pasted AI response and a `.docx` AI result.
9. Confirm a damaged AI response with missing placeholders is routed to review.
10. Distribute the whole `dist\LegalAnonymizer\` folder through the agreed channel. Do not attach release zip files to GitHub unless explicitly requested.

## External Sample Evaluation

Do not commit real client documents. To evaluate real samples locally, pass them to:

```powershell
.\.venv\Scripts\python.exe tools\evaluate_samples.py "D:\path\sample1.docx" "D:\path\sample2.docx" --output-root tmp\sample-evaluation
```

The script copies samples into a local temporary workspace, runs the normal pipeline, and prints JSON metrics without storing source excerpts in the repo.
