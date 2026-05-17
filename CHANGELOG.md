# Changelog

## Unreleased

- README、用户指南、律师转发页新增真实运行截图和更具体的上手步骤。
- 新增主界面、处理完成状态、工作文件夹结构三张说明图，降低非技术用户理解成本。

## 0.2.3

- 发布中文交付说明，方便直接把 GitHub 最新版链接转发给律师用户。
- 在 README 和用户教程中补充最新版下载、旧版本更新、不要下载 Source Code 的说明。
- GitHub Release 页面改为中文固定说明，明确只下载 `LegalAnonymizer.zip`。
- 当前验证口径更新为 55 个测试通过，并覆盖本地复核记忆、历史项目等能力。

## 0.2.2

- 新增本地复核记忆：`加入一定脱敏` 和 `加入一定不脱敏`。
- 新增 `本地规则` 报告，用于查看自动学习、强制脱敏、强制保留的本地规则。
- 新增 `历史项目` 报告，用于查看最近匿名化和还原任务。
- 修复同一词同时出现在强制脱敏和强制保留时的优先级：安全优先，强制脱敏胜出。
- `清空本地学习记忆` 只清理自动学习项，不删除律师手工加入的一定脱敏/一定不脱敏。
- 检测引擎失败时也会记录历史项目，并把文件放入需要复核。

## 0.1.0

- Initial Windows desktop MVP.
- Folder watcher workflow.
- Local anonymization for `.docx`, copyable `.pdf`, `.txt`, and `.md`.
- JSON mapping and Excel comparison table generation.
- AI prompt generation.
- Downloaded-file and pasted-text restore flows.
- Second-pass leakage scan and `02-需要复核-暂勿上传` quarantine folder.
- Regression coverage for English legal headers, English addresses, Chinese party names, and acronym residuals.
- Multi-engine detection pipeline with lightweight Presidio-style recognizers, optional spaCy NER, and legal-document rules.
- Entity source labels in reports and Excel comparison tables.
- PyInstaller Windows distribution.
