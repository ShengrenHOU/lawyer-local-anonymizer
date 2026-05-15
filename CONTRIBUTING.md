# Contributing

## Development Rules

- Keep processing local-first by default.
- Do not add network upload behavior unless it is explicitly opt-in and documented.
- Do not log full client document text.
- Keep original files read-only.
- Keep mapping files out of AI upload folders.

## Checks

Run before submitting changes:

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check src tests
```

For user-facing changes, also run a packaged smoke test with:

```powershell
.\scripts\build_windows.ps1
```

