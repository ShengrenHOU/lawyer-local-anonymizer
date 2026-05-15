# Security Policy

## Security Model

Legal Anonymizer is designed for local document processing.

- It does not upload documents to AI services.
- It generates anonymized files for the user to upload manually.
- Local mapping files are required for restoration and must not be uploaded.
- Reports should avoid full source document text.

## Sensitive Files

Do not share these files publicly:

```text
*.mapping.json
*.脱敏信息对照表.xlsx
99-本地映射表-不要上传/
```

## Reporting Issues

If a document is not anonymized correctly, report:

- file type
- category missed, such as person, company, phone, address, case number
- a minimal synthetic example if possible

Do not send real client files unless a secure review process has been agreed.

