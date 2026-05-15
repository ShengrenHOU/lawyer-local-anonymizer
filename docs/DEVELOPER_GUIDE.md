# Developer Guide

## Project Layout

```text
src/legal_anonymizer/
  config.py          folder names and supported extensions
  workspace.py       workspace creation
  detectors.py       rule-based entity detection
  engines/           multi-engine detection pipeline
  risk_scanner.py    second-pass leakage gate
  mapping_store.py   JSON mapping and Excel comparison table
  anonymizer.py      text replacement
  restore.py         placeholder restore
  document_io.py     docx/pdf/text IO
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

## Release Checklist

1. Run tests and lint.
2. Build Windows distribution.
3. Start `dist\LegalAnonymizer\LegalAnonymizer.exe`.
4. Confirm the five workspace folders are created.
5. Put a sample file into `01-待匿名化`.
6. Confirm anonymized output, JSON mapping, Excel comparison table, report, risk report, and prompt are generated.
7. Restore a pasted AI response.
8. Zip and distribute `dist\LegalAnonymizer.zip`.

## External Sample Evaluation

Do not commit real client documents. To evaluate real samples locally, pass them to:

```powershell
.\.venv\Scripts\python.exe tools\evaluate_samples.py "D:\path\sample1.docx" "D:\path\sample2.docx" --output-root tmp\sample-evaluation
```

The script copies samples into a local temporary workspace, runs the normal pipeline, and prints JSON metrics without storing source excerpts in the repo.
