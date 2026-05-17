# 给律师朋友的最新版使用说明

这是“律师本地匿名化助手”的最新版下载和使用说明。适合直接转发给律师、法务、律师助理。

## 下载

请打开最新版下载页：

[https://github.com/ShengrenHOU/lawyer-local-anonymizer/releases/latest](https://github.com/ShengrenHOU/lawyer-local-anonymizer/releases/latest)

只下载这个文件：

```text
LegalAnonymizer.zip
```

也可以直接点这个下载：

[https://github.com/ShengrenHOU/lawyer-local-anonymizer/releases/latest/download/LegalAnonymizer.zip](https://github.com/ShengrenHOU/lawyer-local-anonymizer/releases/latest/download/LegalAnonymizer.zip)

不要下载 GitHub 自动生成的 `Source code`，也不要点绿色 `Code` 按钮。

## 第一次使用

1. 解压 `LegalAnonymizer.zip`
2. 双击 `LegalAnonymizer.exe`
3. 点击 `放原文件`
4. 把客户 Word 文件放进去
5. 点击 `拿去上传AI`
6. 只上传 `02-已匿名化-可上传AI` 里的文件

## 更新旧版本

如果以前已经用过旧版本：

1. 下载新的 `LegalAnonymizer.zip`
2. 解压到一个新文件夹
3. 双击新的 `LegalAnonymizer.exe`
4. 原来的工作文件夹可以继续保留

不要删除 `99-本地映射表-不要上传`，里面保存还原所需的本地对照表。

## 这版主要升级

- Word 匿名化后仍输出 `.docx`，尽量保留原来的段落、表格、页眉页脚和字体
- 支持把 AI 返回的 Word 或文本结果再本地还原
- 新增 `加入一定脱敏`：漏掉的客户名、公司名、项目名、英文简称，下次优先脱敏
- 新增 `加入一定不脱敏`：普通法律词、模板词被误脱敏时，下次尽量保留
- 新增 `本地规则`：查看本机记住了哪些脱敏/保留规则
- 新增 `历史项目`：查看最近处理过哪些文件、是否通过、是否需要复核
- 如果程序认为仍有风险，文件会进入 `02-需要复核-暂勿上传`

## 三条安全规则

1. 只上传 `02-已匿名化-可上传AI` 里的文件给 AI。
2. 不要上传 `02-需要复核-暂勿上传` 里的文件。
3. 不要上传 `99-本地映射表-不要上传` 里的任何文件。

## 可以转发给律师的短消息

```text
这是最新版“律师本地匿名化助手”。请只下载 LegalAnonymizer.zip，解压后双击 LegalAnonymizer.exe 使用。

下载页：
https://github.com/ShengrenHOU/lawyer-local-anonymizer/releases/latest

直接下载：
https://github.com/ShengrenHOU/lawyer-local-anonymizer/releases/latest/download/LegalAnonymizer.zip

使用时只上传“02-已匿名化-可上传AI”里的文件。不要上传“02-需要复核-暂勿上传”和“99-本地映射表-不要上传”里的任何文件。
```
