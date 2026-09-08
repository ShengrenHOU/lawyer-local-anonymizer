# Codex Kickoff Prompt

> Historical kickoff, not the current task entry (2026-09-08). The app now
> exists in Python/PySide6. Do not replay the phase-zero planning request or
> migrate to C#/WPF unless explicitly asked. Start from root AGENTS.md and
> current code/developer guidance. The original prompt below is preserved;
> its encryption requirement remains an unmet protection, not a waived one.

你要实现一个 Windows 本地小工具：律师本地 Word 匿名化与还原助手。

请先阅读：

1. `docs/PRD.md`
2. `docs/IMPLEMENTATION.md`

然后按以下方式工作：

## 第一条任务

先不要写完整代码。请先输出：

1. 你理解的产品目标。
2. 你建议的 repo 结构。
3. Phase 1 到 Phase 8 的执行计划。
4. 每个 phase 的主要文件、类、测试。
5. 你认为实现中最大的 10 个风险。
6. 你会如何保证不把风险文件误放入“可上传AI”文件夹。

等待我批准计划后，再开始实现。

## 强制约束

1. 不要接入任何云端 API。
2. 不要使用本地大模型。
3. 不要引入 Python。
4. 不要使用 Word COM 自动化。
5. 使用 C# / .NET / WPF / OpenXML。
6. 映射表必须加密，不能明文保存。
7. 原始敏感文本不能写入普通日志。
8. 不能确认安全的文件必须进入 `02-需要复核-暂勿上传`。
9. 先写测试，再逐步实现。
10. 每完成一个阶段都要跑测试并汇报结果。

## MVP 验收目标

1. 拖入 `.docx` 可以自动匿名化。
2. 正文、表格、页眉、页脚、批注中的敏感词可以处理。
3. 公司全称、简称、人名、地址、电话、邮箱、项目名能被高召回替换。
4. 含图片或嵌入对象的文件不能进入可上传文件夹。
5. 匿名文件中的 placeholder 可以在 AI 输出后还原。
6. 所有输出路径符合 PRD 文件夹结构。
