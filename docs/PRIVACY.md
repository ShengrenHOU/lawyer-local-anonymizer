# Privacy Notes

This application is local-first. It does not include AI API calls or cloud upload code.

## Current at-rest protection gap

The application currently saves mappings as ordinary JSON and Excel files
through src/legal_anonymizer/mapping_store.py; it does not encrypt those
files. The encryption requirement in the original PRD remains unmet.
Local-only storage, file hashes and an anonymized-output label are not proof
of encryption, complete de-identification or compliance with all PRD gates.
Do not share mapping directories, local memory, restored outputs or original
documents. This documentation correction does not implement a security fix.

Data that may contain sensitive information:

- original documents in `01-待匿名化`
- mapping files in `99-本地映射表-不要上传`
- Excel comparison tables in `99-本地映射表-不要上传`
- restored documents in `04-已还原`

Only anonymized outputs in `02-已匿名化-可上传AI` are intended for AI upload.
