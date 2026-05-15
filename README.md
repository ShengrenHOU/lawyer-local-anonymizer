# Legal Anonymizer

Legal Anonymizer is a local-first reversible anonymization tool for lawyers who want to use AI chat tools without uploading raw client information.

It replaces sensitive information in Word, copyable PDF, and text files with stable placeholders such as `[[PERSON_001]]` and `[[COMPANY_001]]`. For `.docx` files, it writes an anonymized `.docx` and restores back to `.docx` while preserving most Word layout, tables, headers, footers, and run formatting. After the AI response comes back, the app restores placeholders locally using a private mapping file that never needs to be uploaded.

## What It Does

- Runs locally on Windows.
- Creates a simple five-folder workflow.
- Watches an input folder and anonymizes new files automatically.
- Runs a second-pass leakage scan before allowing upload.
- Uses a multi-engine detection pipeline: lightweight Presidio recognizers, optional spaCy NER, and legal-document rules.
- Generates AI-safe files for Kimi, ChatGPT, or similar tools.
- Keeps `.docx` anonymization and restoration in Word format where possible.
- Generates a local JSON mapping file for restoration.
- Generates a lawyer-readable Excel comparison table.
- Keeps a local learning memory so repeated names, companies, and addresses are recognized more easily over time.
- Writes one per-file result summary explaining whether the output is uploadable and which mapping table belongs to it.
- Restores AI output from downloaded files or pasted text.
- Keeps original files unchanged.

## Folder Workflow

On first launch, the app creates this workspace under the Windows user profile:

```text
律师本地匿名化助手/
  01-待匿名化/
  02-已匿名化-可上传AI/
  02-需要复核-暂勿上传/
  03-AI结果文件-待还原/
  04-已还原/
  99-本地映射表-不要上传/
```

Only files in `02-已匿名化-可上传AI/` should be uploaded to AI tools.

Never upload `99-本地映射表-不要上传/`; it contains the local mapping needed to restore real names and other sensitive values.

If a file lands in `02-需要复核-暂勿上传/`, the automatic leakage scan found high-risk residual content. Do not upload that file to AI.

## Quick Start for End Users

Receive the packaged Windows app folder from the project maintainer, then double-click:

```text
LegalAnonymizer.exe
```

Full user guide: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

## Supported Files

Input anonymization:

- `.docx`, output as anonymized `.docx`
- `.doc`, if Microsoft Word is installed locally for conversion; otherwise save as `.docx` first
- copyable `.pdf`
- `.txt`
- `.md`

AI result restoration:

- `.docx`, restored as `.docx`
- `.txt`
- `.md`
- pasted text

Not supported in the current version:

- scanned PDF
- images
- handwriting
- text inside stamps or screenshots
- encrypted PDF

## Developer Setup

Requirements:

- Windows
- Python 3.11+

Install and run from source:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m legal_anonymizer
```

Run tests:

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check src tests
```

## Build Windows App

```powershell
.\scripts\build_windows.ps1
```

Build outputs:

```text
dist\LegalAnonymizer\LegalAnonymizer.exe
dist\LegalAnonymizer.zip
```

Give the whole `dist\LegalAnonymizer/` folder to the lawyer. The app window itself uses Chinese text.

## Security Model

This project is designed around local processing:

- Original documents stay on the user's computer.
- Mapping files stay on the user's computer.
- The app does not upload files to any AI service.
- The user manually uploads only the anonymized output.
- Logs and reports avoid storing full document text.

Important limitation: automated anonymization can miss entities. Users should quickly review anonymized output before uploading it to an AI tool.

## Detection Architecture

The anonymization pipeline uses multiple detection layers:

```text
text extraction
  -> lightweight Presidio-style recognizers
  -> optional spaCy NER, if a local model is installed
  -> legal-document rules
  -> merged case entity table
  -> placeholder replacement
  -> second-pass leakage scan
      -> pass: 02-已匿名化-可上传AI
      -> fail: 02-需要复核-暂勿上传
```

The app intentionally avoids slow default Presidio NLP startup in the click-to-use path. Presidio-style recognizers handle structured PII locally, while spaCy NER is loaded lazily only if a local model is available.

## Current Validation

Current local validation:

- `pytest`: 24 tests passing
- V2 leakage gate tests cover English legal headers, English addresses, Chinese party names, and acronym residuals
- `ruff`: all checks passing
- packaged smoke: built `LegalAnonymizer.exe` creates the five working folders under an isolated test user profile

## License

MIT License. See [LICENSE](LICENSE).
