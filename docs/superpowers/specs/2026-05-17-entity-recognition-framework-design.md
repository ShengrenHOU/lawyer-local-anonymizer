# Entity Recognition Framework Design

Date: 2026-05-17
Status: Draft for user review
Scope: Next development phase for the existing Python/PySide6 product

## Decision

The next phase prioritizes recognition quality. We will not rewrite the product in C#/.NET, and we will not implement anonymous output filenames in this phase.

We will evolve the current pipeline from:

```text
detectors -> final Entity -> mapping -> replacement
```

to:

```text
detectors / memory / context -> CandidateEntity
  -> CandidateScorer
  -> EntityResolver
  -> ReplacementDecisionEngine
  -> MappingTable
  -> replacement
  -> residual scan and gate
```

The goal is higher recall on legal Word documents while preserving the current folder workflow and packaged Windows executable.

## Problem

The current implementation can detect many entities, but each detector effectively contributes final replacement entities. This creates three recurring issues:

1. A short alias such as `RTS` or `RGL` can be missed because it looks like a generic acronym.
2. A defined term such as `Company` can be either a generic legal word or a case-specific alias, depending on context.
3. Full names, short names, project names, and bracketed aliases are not consistently linked before replacement.

Adding more regular expressions helps individual examples but does not solve the structural issue. The system needs a middle layer that collects suspicious text first, then makes a conservative replacement decision with evidence.

## Design Goals

1. Improve recall for English and Chinese legal Word documents.
2. Treat candidates as evidence first, not final truth.
3. Merge aliases, short names, and defined terms into canonical entities when evidence supports it.
4. Replace uncertain proper nouns in high-risk zones conservatively.
5. Keep the lawyer workflow unchanged: drag file into folder, get pass/review output.
6. Preserve existing tests and real Word smoke tests.
7. Keep external network calls, cloud APIs, local LLMs, OCR, PDF expansion, and C# rewrite out of scope.

## New Core Models

`CandidateEntity`

- `text`: candidate surface text
- `category`: guessed category such as `ORG`, `ORG_ALIAS`, `PERSON`, `ADDRESS`, `MATTER`, `UNKNOWN_PROPER`
- `start` / `end`: offsets in extracted full text
- `source`: detector name such as `company_suffix`, `defined_term`, `legal_context`, `proper_noun`, `memory`
- `score`: initial confidence
- `is_high_risk_zone`: whether it appears in TO/FROM/RE/SUBJECT, first-page zone, header/footer, signature block, table-like context, comments, or footnotes
- `evidence`: short non-sensitive explanation for debugging and risk reports

`CanonicalEntity`

- `entity_id`: stable id such as `ORG_001`
- `category`: canonical category
- `surface_forms`: full original strings to replace
- `aliases`: linked aliases and short names
- `evidence`: candidate references used for the merge

`ReplacementDecision`

- `candidate`: candidate or canonical surface form
- `action`: `replace`, `ignore`, or `review`
- `reason`: non-sensitive decision reason

## Detector Layer

The first implementation should keep current detectors working and add an adapter from existing `Entity` objects to `CandidateEntity`. Then we add or split detectors incrementally:

1. `RegexPiiDetector`: email, phone, ID number, USCC, bank-like numbers near context.
2. `CompanySuffixDetector`: Chinese and English company/law firm suffixes.
3. `DefinedTermAliasDetector`: bracketed aliases, "referred to as", and Chinese short-name patterns.
4. `LegalContextLineDetector`: TO, FROM, CC, RE, SUBJECT, Party A/B, Chinese party labels, contact, director, counsel, authorized representative.
5. `AddressBlockDetector`: English and Chinese address blocks.
6. `ProperNounDetector`: high-risk Title Case phrases, all-caps acronyms, quoted terms, and project/matter titles.
7. `MemoryDetector`: exact and case-normalized matches from local memory.

Detectors only discover candidates. They do not decide final replacement.

## Scoring

`CandidateScorer` assigns final scores using source confidence plus context bonuses.

Baseline source scores:

```text
regex_pii:              100
memory_exact:           100
company_suffix:          95
defined_term_full:       95
defined_term_alias:      90
address_context:         90
legal_context_line:      80
uppercase_acronym:       70
title_case_proper_noun:  55
quoted_term:             55
```

Context bonuses:

```text
header/footer/comment/footnote: +20
TO/FROM/RE/SUBJECT:             +25
signature block:                +25
first page / first 1500 chars:  +15
table-like context:             +15
repeated in document:           +10
near company full name:         +15
```

Conservative replacement thresholds:

```text
score >= 75: replace
score >= 55 and high-risk zone: replace
defined-term alias: replace
uppercase acronym repeated >= 2 and not allowlisted: replace
conflicting or structurally suspicious evidence: review
```

## Entity Resolution

`EntityResolver` groups related candidates before mapping generation.

Rules for the first slice:

1. Exact same surface form maps to the same replacement.
2. Case-normalized same English surface maps together.
3. Full company name plus bracket alias are grouped as one canonical organization.
4. Company full name and suffix-stripped short name are grouped when the short name appears in high-risk zones.
5. All-caps aliases near a full company name are grouped with that company.
6. Matter/project title candidates remain separate unless clearly derived from an organization name.
7. Uncertain high-risk proper nouns become `UNKNOWN_PROPER` or `MATTER`, not ignored.

Mapping should still preserve surface-level restoration. Even if `Rockit Trading (Shanghai) Co., Ltd.`, `RTS`, and `Rockit Trading` are one canonical entity, each surface form must restore to its original exact text.

## Replacement Decisions

`ReplacementDecisionEngine` converts scored candidates and canonical entities into final mapping entries.

It must:

1. Prefer longer overlapping candidates.
2. Avoid crossing or conflicting replacement spans.
3. Preserve the current placeholder format for now unless a later phase approves checksum placeholders.
4. Record source and evidence in the mapping object without writing sensitive text into ordinary logs.
5. Send ambiguous conflicts to review rather than silently passing.

## Pipeline Integration

The current `detect_entities_multi_engine(text) -> list[Entity]` call should be wrapped, not deleted immediately.

Target flow:

```text
read_text_document
  -> detect raw Entity values through existing engines
  -> adapt Entity to CandidateEntity
  -> run new candidate detectors
  -> score candidates
  -> resolve canonical entities
  -> decide replacements
  -> build MappingTable
  -> anonymize text/docx
  -> residual scan
  -> pass or review gate
```

This allows the product to keep working while the recognition layer is upgraded.

## Error Handling And Gate

The gate remains fail-closed.

Review is required when:

1. Detection or scoring raises a non-recoverable error.
2. Candidate spans overlap in a way the decision engine cannot resolve.
3. High-risk zones contain unknown proper nouns below replacement threshold but above review threshold.
4. Residual scan finds original surface forms after replacement.
5. Unsupported Word structures are present.

Risk reports should name categories and reasons without echoing raw sensitive values.

## Tests

Unit tests:

1. Candidate adapter from existing `Entity`.
2. Candidate scoring thresholds and high-risk bonuses.
3. Defined-term alias grouping.
4. Company short-name grouping.
5. Uppercase acronym allowlist and replacement decisions.
6. Overlap resolution prefers longer and higher-confidence spans.
7. Unknown high-risk proper noun becomes replacement or review, not pass-through.

Integration tests:

1. English memo with TO/FROM/RE, company full names, aliases, people, addresses, and project title.
2. Chinese contract with party labels, legal representative, signer, USCC, and signing location.
3. Word header/footer/comment text participates in candidate detection.
4. Real Word smoke test still produces a `.docx` output and passes or reviews according to gate findings.

## First Implementation Slice

The first implementation slice should be small:

1. Add `CandidateEntity`, `CanonicalEntity`, and `ReplacementDecision` models.
2. Add adapter from current `Entity` to `CandidateEntity`.
3. Add `CandidateScorer`.
4. Add a narrow `DefinedTermAliasDetector` for `Full Name ("ALIAS")` and Chinese short-name definitions.
5. Add `EntityResolver` for full-name and alias grouping.
6. Feed final decisions back into the existing `MappingTable`.
7. Add focused unit tests and one English memo integration test.

This slice should not change UI, packaging flow, output filename policy, or mapping encryption.

## Out Of Scope For This Phase

1. C#/.NET/WPF rewrite.
2. Cloud API or local LLM.
3. OCR and PDF.
4. Anonymous output filenames.
5. DPAPI mapping encryption.
6. New checksum placeholder format.
7. Full knowledge graph UI.
8. Manual per-entity review workflow.

## Acceptance Criteria

The phase is complete when:

1. Existing tests still pass.
2. New scoring and alias-resolution tests pass.
3. An English memo fixture replaces company full names, bracket aliases, TO/FROM people, address blocks, and matter/project title candidates.
4. A real Word smoke test runs through the packaged executable.
5. Completion report separates unit tests, integration tests, and real smoke.
