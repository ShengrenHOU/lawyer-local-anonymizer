# Legal Anonymizer

Legal Anonymizer is a local-first reversible anonymization tool for lawyers who want to use AI chat tools without uploading raw client information.

## Download for Lawyers

Download the latest Windows package here:

[Latest release](https://github.com/ShengrenHOU/lawyer-local-anonymizer/releases/latest)

Direct download:

[LegalAnonymizer.zip](https://github.com/ShengrenHOU/lawyer-local-anonymizer/releases/latest/download/LegalAnonymizer.zip)

Use it like this:

1. Download `LegalAnonymizer.zip`.
2. Extract the zip file.
3. Double-click `LegalAnonymizer.exe`.
4. Put client `.docx` files into `01-待匿名化`.
5. Upload only files from `02-已匿名化-可上传AI`.
6. Do not upload anything from `99-本地映射表-不要上传`.

Do not download the source code zip from GitHub. Lawyer users should download only `LegalAnonymizer.zip` from Releases.

## What It Does

- Runs locally on Windows.
- Creates a simple folder workflow.
- Watches an input folder and anonymizes new files automatically.
- Keeps `.docx` anonymization and restoration in Word format where possible.
- Preserves most Word layout, tables, headers, footers, and run formatting.
- Uses placeholders such as `[[PERSON_001]]` and `[[COMPANY_001]]`.
- Runs a second-pass leakage scan before allowing upload.
- Routes risky files to a review folder instead of the uploadable folder.
- Generates a local JSON mapping file and lawyer-readable Excel comparison table.
- Keeps a local learning memory so repeated names, companies, and addresses are recognized more easily over time.
- Restores downloaded AI output files or pasted AI text.
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

If a file lands in `02-需要复核-暂勿上传/`, do not upload that file to AI. The local scan found high-risk residual content, an unsupported Word structure, a detector failure, or damaged placeholders in an AI result.

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

## User Guide

Full user guide: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

Security and privacy notes: [docs/PRIVACY.md](docs/PRIVACY.md)

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
.\.venv\Scripts\python -m ruff check src tests tools
```

Build Windows app:

```powershell
.\scripts\build_windows.ps1
```

Build outputs:

```text
dist\LegalAnonymizer\LegalAnonymizer.exe
dist\LegalAnonymizer.zip
```

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
  -> candidate entity scoring and alias resolution
  -> merged case entity table
  -> placeholder replacement
  -> second-pass leakage scan
      -> pass: 02-已匿名化-可上传AI
      -> fail: 02-需要复核-暂勿上传
```

The app intentionally avoids slow default Presidio NLP startup in the click-to-use path. Presidio-style recognizers handle structured PII locally, while spaCy NER is loaded lazily only if a local model is available.

## Current Validation

Current validation:

- `pytest`: 43 tests passing
- `ruff`: all checks passing
- Packaged smoke: built `LegalAnonymizer.exe` processed a real Word contract under an isolated test user profile
- Leakage gate tests cover English legal headers, English addresses, Chinese company/institution names, Chinese addresses, Chinese party-name contexts, acronym residuals, unsupported Word structures, and defined-term aliases

## License

MIT License. See [LICENSE](LICENSE).
