# 实现文档：律师本地 Word 匿名化与还原小工具

版本：v0.1 MVP  
开发目标：让 Codex 可以直接据此创建仓库、实现核心功能和测试。  
优先级：先做一个稳定、保守、可运行的小工具；不要上本地大模型；不要接外部 API。

---

## 1. 技术原则

1. 本地运行，不允许网络调用。
2. MVP 不使用云端 API，不使用本地 LLM。
3. 优先使用 C# / .NET 实现，减少 Python 环境依赖。
4. Word 处理基于 OpenXML，不通过 Word COM 自动化。
5. 规则与配置可外置，便于后续调整。
6. 安全策略采用 fail-closed：不能确认安全就进入复核。
7. 不追求低误报，优先降低漏报。
8. 映射表必须加密。
9. 任何处理错误都不能静默失败。

---

## 2. 推荐技术栈

```text
语言：C#
框架：.NET 8 或当前稳定 LTS .NET
桌面 UI：WPF
Word 处理：DocumentFormat.OpenXml
文件监听：FileSystemWatcher
加密：Windows DPAPI / ProtectedData
配置：JSON
测试：xUnit
日志：Microsoft.Extensions.Logging，必要时加 Serilog
打包：MSIX 或单文件 exe，MVP 可先 dotnet publish
```

MVP 暂不使用：

```text
Python
Presidio
spaCy
Ollama
本地 LLM
OCR
云端 API
数据库
```

理由：这是律师电脑上的小工具，安装和维护复杂度必须低。确定性规则 + OpenXML 全覆盖 + 保守门禁更适合第一版。

---

## 3. 仓库结构

建议 Codex 创建以下结构：

```text
legal-local-anonymizer/
  README.md
  AGENTS.md
  docs/
    PRD.md
    IMPLEMENTATION.md
  src/
    LegalAnon.App/
      LegalAnon.App.csproj
      App.xaml
      MainWindow.xaml
      MainWindow.xaml.cs
      appsettings.json
    LegalAnon.Core/
      LegalAnon.Core.csproj
      Domain/
      Detection/
      Mapping/
      Gate/
      Restore/
      Config/
      Utilities/
    LegalAnon.OpenXml/
      LegalAnon.OpenXml.csproj
      Extraction/
      Replacement/
      Metadata/
      Validation/
    LegalAnon.Tests/
      LegalAnon.Tests.csproj
      Fixtures/
      Unit/
      Integration/
  config/
    rules.json
    allowlist.json
    settings.template.json
  samples/
    README.md
```

---

## 4. 核心模块

### 4.1 LegalAnon.App

职责：

1. WPF 主界面。
2. 工作区选择与初始化。
3. 文件夹按钮。
4. 文件夹监听。
5. 重新扫描按钮。
6. 最近任务状态展示。
7. 调用 Core 处理任务。

不要把脱敏逻辑写在 UI 层。

---

### 4.2 LegalAnon.Core

职责：

1. Job 编排。
2. 候选实体发现。
3. 实体归并。
4. 映射表生成和加密。
5. 风险门禁。
6. 还原逻辑。
7. 配置加载。

---

### 4.3 LegalAnon.OpenXml

职责：

1. 从 `.docx` 提取文本节点。
2. 建立 text span index。
3. 对 OpenXML 文本节点做原位替换。
4. 清理 metadata。
5. 检查不支持结构。
6. 验证输出文档能打开。

---

## 5. 领域模型

Codex 应创建以下核心类。

### 5.1 DocumentJob

```csharp
public sealed class DocumentJob
{
    public string JobId { get; init; }
    public string SourcePath { get; init; }
    public string SourceFileName { get; init; }
    public string SourceFileHash { get; init; }
    public DateTimeOffset CreatedAt { get; init; }
    public JobType Type { get; init; } // Anonymize or Restore
}
```

### 5.2 TextSpan

```csharp
public sealed class TextSpan
{
    public string SpanId { get; init; }
    public string PartId { get; init; }
    public string PartKind { get; init; } // Body, Header, Footer, Footnote, Comment, Metadata, etc.
    public int GlobalStart { get; init; }
    public int GlobalEnd { get; init; }
    public string Text { get; init; }
    public bool IsHighRiskZone { get; init; }
    public string LocationHint { get; init; }
}
```

### 5.3 CandidateEntity

```csharp
public sealed class CandidateEntity
{
    public string Text { get; init; }
    public int Start { get; init; }
    public int End { get; init; }
    public EntityType Type { get; init; }
    public string Source { get; init; } // Regex, CompanySuffix, DefinedTerm, ProperNoun, Context, Memory
    public double Score { get; init; }
    public string PartKind { get; init; }
    public bool IsHighRiskZone { get; init; }
    public string Evidence { get; init; }
}
```

### 5.4 CanonicalEntity

```csharp
public sealed class CanonicalEntity
{
    public string EntityId { get; init; } // ORG_001, PERSON_001
    public EntityType Type { get; init; }
    public List<string> SurfaceForms { get; init; }
    public List<string> Aliases { get; init; }
    public List<CandidateEntity> Evidence { get; init; }
}
```

### 5.5 MappingEntry

```csharp
public sealed class MappingEntry
{
    public string Placeholder { get; init; }
    public string Original { get; init; }
    public string EntityId { get; init; }
    public EntityType EntityType { get; init; }
    public string SurfaceRole { get; init; } // FULL, ALIAS, SHORT, UNKNOWN
    public string Checksum { get; init; }
}
```

### 5.6 ReplacementPlanItem

```csharp
public sealed class ReplacementPlanItem
{
    public int Start { get; init; }
    public int End { get; init; }
    public string Original { get; init; }
    public string Replacement { get; init; }
    public string EntityId { get; init; }
}
```

### 5.7 GateReport

```csharp
public sealed class GateReport
{
    public string JobId { get; init; }
    public GateDecision Decision { get; init; } // Pass, Review, Error
    public List<RiskFinding> Findings { get; init; }
    public Dictionary<string, int> EntityCounts { get; init; }
}
```

---

## 6. 工作区初始化

实现 `WorkspaceService`。

### 6.1 方法

```csharp
public sealed class WorkspaceService
{
    public Workspace Initialize(string rootPath);
    public bool IsValidWorkspace(string rootPath);
    public Workspace LoadFromSettings();
}
```

### 6.2 必须创建的目录

```text
01-待匿名化
02-已匿名化-可上传AI
02-需要复核-暂勿上传
03-AI结果放这里
04-已还原
99-本地映射表-不要上传
logs
config
```

---

## 7. 文件监听

实现 `FolderWatcherService`。

监听：

```text
01-待匿名化/*.docx
03-AI结果放这里/*.docx, *.txt, *.md
```

### 7.1 文件稳定性检查

复制大文件时，FileSystemWatcher 可能提前触发。实现：

```csharp
Task WaitForFileReadyAsync(string path, CancellationToken ct)
```

逻辑：

1. 每 500ms 检查一次文件大小和最后修改时间。
2. 连续 2 秒无变化，再处理。
3. 尝试以读共享方式打开文件。
4. 超时则写入错误报告。

---

## 8. OpenXML 文本抽取

实现 `DocxTextExtractor`。

### 8.1 输入输出

```csharp
public sealed class DocxTextExtractor
{
    public ExtractedDocument Extract(string docxPath);
}
```

`ExtractedDocument` 包含：

```csharp
public sealed class ExtractedDocument
{
    public string FullText { get; init; }
    public List<TextSpan> Spans { get; init; }
    public List<UnsupportedPartFinding> UnsupportedParts { get; init; }
    public List<MetadataText> MetadataTexts { get; init; }
}
```

### 8.2 抽取策略

1. 打开 `.docx` package。
2. 遍历 WordprocessingDocument 的 main document part。
3. 遍历 HeaderParts、FooterParts、FootnotesPart、EndnotesPart、WordprocessingCommentsPart。
4. 对每个 OpenXmlPart，收集所有 `DocumentFormat.OpenXml.Wordprocessing.Text` 节点。
5. 为每个文本节点建立 global offset。
6. 在不同 block / paragraph 之间插入换行符到 `FullText`，方便行级规则检测。
7. 记录每个 span 的 part 类型和位置。

### 8.3 高风险区域标记

以下位置标记 `IsHighRiskZone = true`：

1. Header。
2. Footer。
3. Comments。
4. Footnotes / Endnotes。
5. 前 1500 个字符。
6. 包含 TO / FROM / CC / RE / SUBJECT / ATTENTION 的行。
7. 包含 甲方 / 乙方 / 丙方 / 签署 / 授权代表 / 联系人 / 地址 的行。
8. 表格中标签为 Name / Address / Contact / Company / Director / Counsel 的邻近文本。

MVP 可以先通过文本行关键词标记，不必精确理解表格结构。

### 8.4 不支持结构检查

实现 `DocxUnsupportedPartScanner`。

若发现以下结构，加入 finding：

1. 图片 drawing / blip。
2. OLE object。
3. Embedded package。
4. 受保护或加密状态。
5. tracked deletion text。

配置 `failOnImages = true` 时，图片直接导致 Review。

---

## 9. 候选实体检测器

所有检测器实现统一接口：

```csharp
public interface IEntityDetector
{
    IReadOnlyList<CandidateEntity> Detect(DetectionContext context);
}
```

`DetectionContext`：

```csharp
public sealed class DetectionContext
{
    public string FullText { get; init; }
    public IReadOnlyList<TextSpan> Spans { get; init; }
    public RuleConfig Rules { get; init; }
    public AllowlistConfig Allowlist { get; init; }
    public CaseMemory Memory { get; init; }
}
```

### 9.1 RegexPiiDetector

检测：

1. Email。
2. Phone。
3. URL / domain。
4. Chinese ID number。
5. Passport-like numbers near passport context。
6. Unified Social Credit Code。
7. Bank account near bank context。
8. Tax ID / registration number near context。

输出高分候选。

---

### 9.2 CompanySuffixDetector

英文公司后缀：

```text
Co., Ltd.
Company Limited
Limited
Ltd.
LLC
LLP
Inc.
Corporation
Corp.
Holdings
Group
Pte. Ltd.
GmbH
AG
B.V.
S.A.
Pty Ltd
```

中文机构后缀：

```text
有限公司
有限责任公司
股份有限公司
集团
合伙企业
律师事务所
事务所
银行
委员会
基金
研究院
```

策略：

1. 从后缀向前扩展若干词，得到完整公司名。
2. 避免跨段落扩展。
3. 命中后输出 `ORG`。

---

### 9.3 DefinedTermAliasDetector

检测定义词和简称。

英文模式：

```text
Full Company Name ("RGL")
Full Company Name ('RGL')
Full Company Name (RGL)
hereinafter referred to as the "Company"
referred to as "Buyer"
```

中文模式：

```text
北京某某有限公司（以下简称“甲方”）
北京某某有限公司（简称“某某公司”）
甲方：北京某某有限公司
乙方：张三
```

输出：

1. full name candidate。
2. alias candidate。
3. relation hint：alias belongs to full name。

---

### 9.4 LegalContextLineDetector

逐行扫描以下关键词：

```text
TO:
FROM:
CC:
BCC:
ATTENTION:
RE:
SUBJECT:
Client:
Counsel:
Director:
Contact:
Address:
Party A:
Party B:
甲方
乙方
丙方
联系人
地址
签署地
授权代表
法定代表人
董事
律师
```

策略：

1. 对冒号后的值做候选拆分。
2. 英文 Title Case 片段 -> PERSON / ORG / MATTER 候选。
3. 全大写 2-8 字母 -> ORG_ALIAS 候选，除非在 allowlist。
4. 中文 2-4 字符，在姓名/联系人/代表上下文 -> PERSON 候选。
5. 地址上下文整段 -> ADDRESS 候选。

---

### 9.5 ProperNounDetector

用于保守发现未知专有名词。

检测：

1. 英文连续 Title Case：`Project Falcon`, `Rockit Trading`, `Blue River Energy`。
2. 全大写缩写：`RGL`, `RTC`, `RTS`。
3. 引号中的短语。
4. 标题中的非通用专有名词。
5. 括号中的 2-20 字符 alias。

替换策略不在 detector 中决定。Detector 只输出候选。

---

### 9.6 AddressBlockDetector

上下文关键词：

```text
Address
Registered Office
Office
Residence
Located at
Level
Floor
Room
Suite
Building
Road
Street
Avenue
District
Province
Postal Code
地址
住所
联系地址
注册地址
签署地
房间
楼
路
街
区
市
省
邮编
```

策略：

1. 命中地址标签时，取同一行冒号后的文本。
2. 如果下一行继续包含地址词，也并入。
3. 英文地址中包含数字 + street/road/floor/level 等，输出 ADDRESS。
4. 中文地址中包含省/市/区/路/号/楼/室，输出 ADDRESS。

---

### 9.7 MetadataDetector

扫描：

1. 原始文件名。
2. Word core properties：title、subject、creator、lastModifiedBy、description。
3. Extended properties：company、manager。
4. Custom properties。

输出 `DOC_META` 候选。

---

### 9.8 MemoryDetector

从本地 case memory 中读取已知 surface forms。

MVP 可先实现简单 exact match：

1. 解密 `case_memory.enc`。
2. 对其中 surface forms 做精确匹配和大小写归一匹配。
3. 输出候选。

---

## 10. 候选过滤与替换决策

实现 `CandidateScorer` 和 `ReplacementDecisionEngine`。

### 10.1 分数建议

```text
Regex PII:              100
Company suffix:          95
Defined term full name:  95
Defined term alias:      90
Address context:         90
Legal context line:      80
Memory exact match:      100
Uppercase acronym:       70
Title Case proper noun:  55
Quoted term:             55
```

Zone 加分：

```text
Header/Footer: +20
TO/FROM/RE/SUBJECT: +25
Signature block: +25
First page / first 1500 chars: +15
Table-like context: +15
```

### 10.2 替换阈值

保守模式：

```text
score >= 75: 替换
score >= 55 且 IsHighRiskZone: 替换
全大写缩写重复出现 >= 2 次且不在 allowlist: 替换
定义词 alias: 替换
```

### 10.3 不替换内容

1. allowlist 中的通用法律词。
2. 日期，如果不包含客户线索。
3. 金额，MVP 可不替换；后续可配置。
4. 国家名和城市名是否替换由配置决定。默认具体地址替换，单独国家名不替换。

---

## 11. 实体归并

实现 `EntityResolver`。

### 11.1 归并规则

1. 完全相同 surface form -> 同一 mapping entry。
2. 大小写归一相同 -> 同一 mapping entry。
3. 定义词规则中 full + alias -> 同一 canonical entity，但不同 mapping entry。
4. 公司全称与去后缀短名可归为同一 canonical entity。
5. 全大写 alias 如果在公司全称附近括号中出现，归入该公司。
6. 不确定的 proper noun 单独成 `UNKNOWN` 或 `MATTER`。

### 11.2 surface role

```text
FULL
ALIAS
SHORT
ROLE
UNKNOWN
```

---

## 12. 占位符生成

实现 `PlaceholderService`。

格式：

```text
[[{TYPE}_{NNN}_{ROLE}_{CHK}]]
```

示例：

```text
[[ORG_001_FULL_A7F]]
[[ORG_001_ALIAS_B2K]]
[[PERSON_001_FULL_M9Q]]
[[ADDRESS_001_FULL_D8X]]
```

Checksum：

1. 使用 placeholder 核心字段 + jobId + secret salt。
2. 计算 SHA256。
3. 取前 3 位大写 base32 或 hex 字符。

注意：checksum 不是安全加密，只用于减少误还原。

---

## 13. OpenXML 替换

实现 `DocxReplacementEngine`。

### 13.1 方法

```csharp
public sealed class DocxReplacementEngine
{
    public void ApplyReplacements(
        string sourceDocxPath,
        string outputDocxPath,
        IReadOnlyList<ReplacementPlanItem> replacements,
        ReplacementOptions options);
}
```

### 13.2 替换算法

1. 复制原始 `.docx` 到输出路径。
2. 重新打开输出文档。
3. 对每个 OpenXML part 重新构建 TextNodeRef。
4. 将 global replacement span 映射到 TextNodeRef。
5. 对每个 replacement：
   - 如果在单个 text node 中，直接 substring 替换。
   - 如果跨多个 text node：
     - 第一个 node 保留 span 前文本 + placeholder。
     - 中间 node 清空。
     - 最后 node 保留 span 后文本。
6. 从后往前处理，避免 offset 变化影响。
7. 保存文档。
8. 清理 metadata。
9. 验证文档可重新打开。

### 13.3 重叠处理

Replacement plan 生成前必须处理重叠：

1. 长实体优先。
2. 高分实体优先。
3. 起止位置完全包含时保留外层实体。
4. 不允许两个 replacement 交叉重叠。

---

## 14. Metadata 清理

实现 `DocxMetadataSanitizer`。

清理字段：

```text
Title
Subject
Creator
LastModifiedBy
Description
Keywords
Category
Company
Manager
CustomProperties
```

替换为：

```text
Anonymous Document
Legal Local Anonymizer
```

或空值。

---

## 15. 映射表加密

实现 `MappingStore`。

### 15.1 文件位置

```text
99-本地映射表-不要上传/{jobId}.mapping.json.enc
99-本地映射表-不要上传/case_memory.enc
```

### 15.2 加密方式

MVP 使用 Windows DPAPI：

```csharp
ProtectedData.Protect(bytes, optionalEntropy, DataProtectionScope.CurrentUser)
ProtectedData.Unprotect(bytes, optionalEntropy, DataProtectionScope.CurrentUser)
```

含义：

1. 同一 Windows 用户可以解密。
2. 其他用户或其他机器默认不能解密。
3. 无需用户记密码。

### 15.3 映射查询

还原时通过 placeholder 查找 mapping：

1. 扫描所有 mapping 文件。
2. 建立 placeholder -> original 字典。
3. 找到命中最多的 job mapping。
4. 如果多个 mapping 冲突，生成 warning，要求复核。

---

## 16. 残留扫描

实现 `ResidualScanner`。

输入：

```text
匿名化 docx 路径
mapping entries
allowlist
```

检查：

1. 对所有 original surface forms 做 exact scan。
2. 做 lower-case scan。
3. 做 normalized scan：去空格、去常见标点、全角半角归一。
4. 重新运行 detectors，但忽略合法 placeholder。
5. 扫描 metadata 和文件名。

输出：

```csharp
List<RiskFinding>
```

风险等级：

```text
Critical: 已识别原文残留
High: 匿名文档中出现新高风险实体候选
Medium: 未支持结构存在
Low: 普通提示
```

---

## 17. 门禁引擎

实现 `GateEngine`。

### 17.1 Pass 条件

全部满足才 Pass：

1. UnsupportedParts 为空。
2. ResidualScanner 无 Critical / High finding。
3. 映射表写入成功。
4. metadata 已清理。
5. placeholder 格式完整。
6. 输出 docx 可打开。

### 17.2 Review 条件

任何一个满足即 Review：

1. 有图片。
2. 有 OLE。
3. 有无法解析的 part。
4. 有已识别原文残留。
5. 有高风险未知专有名词。
6. 替换失败。
7. metadata 清理失败。
8. 映射表加密失败。

### 17.3 输出路径

Pass：

```text
02-已匿名化-可上传AI/匿名化_{timestamp}_{jobSeq}.docx
```

Review：

```text
02-需要复核-暂勿上传/需复核_{timestamp}_{jobSeq}.docx
02-需要复核-暂勿上传/需复核_{timestamp}_{jobSeq}_风险报告.txt
```

---

## 18. 风险报告生成

实现 `RiskReportWriter`。

原则：

1. 报告不要包含完整原始敏感文本。
2. 可以写位置、类型、原因。
3. 语言必须非技术。
4. 明确提示“不要上传”。

模板：

```text
处理结果：暂勿上传

系统已生成匿名化版本，但未能确认完全安全，因此没有放入“可上传AI”文件夹。

主要原因：
1. 页眉区域发现疑似未处理的公司简称。
2. 文档包含图片，系统无法确认图片中是否有客户信息。
3. 签署页附近发现疑似地址。

建议：
请人工复核该文件。复核前不要上传给任何外部 AI。
```

Pass 文件旁边生成摘要：

```text
处理结果：可上传

已替换：
公司/组织：5
人名：8
地址：3
联系方式：6
项目/交易名：2
未知专有名词：4

本地映射表已加密保存。
```

---

## 19. 还原引擎

实现 `RestoreService`。

支持：

```text
.docx
.txt
.md
```

### 19.1 txt / md 还原

1. 读取文本。
2. 正则扫描 placeholder。
3. 查 mapping。
4. 替换。
5. 输出到 `04-已还原`。

### 19.2 docx 还原

1. 使用 OpenXML 抽取 text nodes。
2. 扫描 placeholder。
3. 生成 replacement plan。
4. 使用同一个 replacement engine 替换。
5. 输出 docx。

### 19.3 placeholder 容错

允许轻微空格：

```text
[[ ORG_001_FULL_A7F ]]
```

不允许：

1. checksum 缺失。
2. 类型/编号/校验码不匹配。
3. 多个 mapping 冲突。

这些情况生成 warning report。

---

## 20. UI 实现

### 20.1 MainWindow

显示：

```text
律师本地脱敏助手
状态：运行中
工作区：C:\...\LegalAnonWorkspace

按钮：
[打开待匿名化文件夹]
[打开可上传AI文件夹]
[打开需要复核文件夹]
[打开AI结果文件夹]
[打开已还原文件夹]
[重新扫描]
[设置]

最近处理：
时间 | 文件 | 结果 | 原因
```

### 20.2 状态颜色

```text
绿色：处理成功，可上传
红色：需要复核，暂勿上传
黄色：处理中
灰色：等待文件
```

### 20.3 系统托盘

MVP 可选。若实现，提供：

1. 打开主界面。
2. 打开工作区。
3. 重新扫描。
4. 退出。

---

## 21. 配置文件

### 21.1 rules.json

结构示例：

```json
{
  "companySuffixesEnglish": ["Co., Ltd.", "Limited", "Ltd.", "LLC", "LLP", "Inc.", "Corporation", "Corp.", "Holdings", "Group", "Pte. Ltd.", "GmbH", "AG", "B.V.", "S.A.", "Pty Ltd"],
  "companySuffixesChinese": ["有限公司", "有限责任公司", "股份有限公司", "集团", "合伙企业", "律师事务所", "事务所", "银行", "委员会", "基金", "研究院"],
  "highRiskLineKeywords": ["TO:", "FROM:", "CC:", "ATTENTION:", "RE:", "SUBJECT:", "甲方", "乙方", "联系人", "地址", "签署地", "授权代表", "董事", "律师"],
  "addressKeywords": ["Address", "Registered Office", "Level", "Floor", "Room", "Road", "Street", "District", "Province", "地址", "住所", "联系地址", "注册地址", "签署地", "路", "街", "区", "市", "省"]
}
```

### 21.2 allowlist.json

```json
{
  "uppercaseAcronyms": ["NDA", "SPA", "MOU", "LOI", "VAT", "USD", "RMB", "PRC", "HK", "EU", "UK", "US"],
  "legalTerms": ["Agreement", "Contract", "Schedule", "Annex", "Clause", "Party", "Parties", "Buyer", "Seller", "Client", "Counsel"]
}
```

注意：`Buyer`, `Seller`, `Client`, `Counsel` 作为角色词可以不替换，但如果它们是定义词 alias，也可以替换为角色 placeholder。MVP 可以先保留角色词。

---

## 22. 测试计划

### 22.1 Unit tests

必须测试：

1. Email/phone/id regex。
2. Company suffix detection。
3. Defined term alias detection。
4. Proper noun detection。
5. Candidate scoring。
6. Placeholder generation。
7. Mapping encryption/decryption。
8. Residual normalized scan。
9. Gate decisions。

### 22.2 Integration tests

用代码生成或使用 fixture docx：

1. 正文公司名替换。
2. 页眉公司简称替换。
3. 页脚地址替换。
4. 表格联系人替换。
5. 批注律师姓名替换。
6. 跨 run placeholder 替换。
7. 含图片文件进入 review。
8. metadata 清理。
9. AI txt 输出还原。
10. AI docx 输出还原。

### 22.3 Acceptance test sample

输入文档包含：

```text
TO: John Smith, Director, RGL
FROM: Mary Chen, Counsel
RE: Rockit Trading Shanghai Restructuring

Rockit Trading (Shanghai) Co., Ltd. ("RGL")
Address: Level 12, 188 Century Avenue, Pudong, Shanghai
甲方：上海某某贸易有限公司
签署地：上海市浦东新区
```

通过后匿名文件中不得出现：

```text
John Smith
Mary Chen
RGL
Rockit Trading
Rockit Trading (Shanghai) Co., Ltd.
Level 12
Century Avenue
Pudong
上海某某贸易有限公司
上海市浦东新区
```

---

## 23. 实现顺序

Codex 应按以下顺序实现，不要一开始做 UI 美化。

### Phase 1：项目骨架

1. 创建 solution 和项目结构。
2. 创建核心 domain models。
3. 创建 WorkspaceService。
4. 创建基础配置加载。
5. 创建测试项目。

### Phase 2：OpenXML 抽取与替换

1. 实现 DocxTextExtractor。
2. 实现 TextSpan index。
3. 实现 DocxReplacementEngine。
4. 实现 MetadataSanitizer。
5. 写 integration tests。

### Phase 3：检测器

1. RegexPiiDetector。
2. CompanySuffixDetector。
3. DefinedTermAliasDetector。
4. LegalContextLineDetector。
5. ProperNounDetector。
6. AddressBlockDetector。
7. MetadataDetector。

### Phase 4：实体归并与映射

1. CandidateScorer。
2. ReplacementDecisionEngine。
3. EntityResolver。
4. PlaceholderService。
5. MappingStore 加密。

### Phase 5：匿名化 pipeline

1. AnonymizationService。
2. ResidualScanner。
3. GateEngine。
4. RiskReportWriter。
5. 输出到正确文件夹。

### Phase 6：还原 pipeline

1. RestoreService。
2. txt/md restore。
3. docx restore。
4. unknown placeholder warning。

### Phase 7：WPF UI 与文件监听

1. MainWindow。
2. 文件夹按钮。
3. FileSystemWatcher。
4. 重新扫描。
5. 最近任务列表。

### Phase 8：打包与最终测试

1. dotnet publish。
2. README 使用说明。
3. 手动 smoke test。
4. 样例文件测试。

---

## 24. Codex 开发约束

请 Codex 严格遵守：

1. 不引入网络调用。
2. 不引入云端 AI API。
3. 不引入本地大模型。
4. 不引入 Python 依赖。
5. 不使用 Word COM 自动化。
6. 不把敏感原文写入普通日志。
7. 不把映射表明文保存。
8. 所有风险情况必须进入 review 或 error，不得放行。
9. 每完成一个 Phase，先跑测试，再继续下一个 Phase。
10. 优先可运行和可测试，不追求 UI 漂亮。

---

## 25. 最小 README 内容

README 应包括：

1. 产品用途。
2. 安装/运行方式。
3. 文件夹说明。
4. 如何匿名化。
5. 如何还原。
6. 什么情况下不能上传。
7. 安全声明：本工具降低风险，但不能替代律师人工判断。
8. 开发与测试命令。

---

## 26. MVP 完成定义

当以下条件满足时，v0.1 MVP 视为完成：

1. 用户能启动 Windows 程序。
2. 程序能创建工作区文件夹。
3. 拖入 `.docx` 后能自动生成匿名化文件。
4. 安全文件进入 `02-已匿名化-可上传AI`。
5. 风险文件进入 `02-需要复核-暂勿上传`。
6. 映射表加密保存。
7. AI 输出 `.txt` / `.md` / `.docx` 能还原。
8. 页眉、页脚、表格、批注至少有测试覆盖。
9. 含图片文件不被放行。
10. 测试集中的敏感字符串匿名化后无残留。

