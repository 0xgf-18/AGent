# Index File Formats

> **Scope:** Templates for all index files in the wiki.
> **Load when:** Creating or updating indexes during compile or reindex.
> **See also:** [write-pipeline.md](write-pipeline.md)

---

## 1. `_master-index.md` — Wiki Root

```markdown
# Knowledge Base Master Index
Last reindexed: YYYY-MM-DD | Total articles: N

## Quick Navigation — "I want to..."
- Hook a native function → [[wiki/frida/_index]]
- Understand DexGuard obfuscation → [[wiki/obfuscation/_index]]
- Find a working cert pinning bypass → [[wiki/rasp/_index]] or check [[wiki/_snippets-index]]
- Analyze an APK → [[wiki/apk/_index]]
- Find unpacking techniques → [[wiki/techniques/_index]]
- Check experiment history → [[wiki/experiments/_index]]
- View success traces → [[wiki/success-traces/_index]]
- Check packer unpacking methods → [[wiki/packers/_index]] (environment state is runtime-only: run `env_probe.py --health`)
- Browse tool registry → [[wiki/tool-registry/_index]]
- Find protection patterns → [[wiki/patterns/_index]]
- View knowledge diffs → [[wiki/knowledge-diffs/_index]]

## Topic Index
| Topic | Description | Articles | Last updated |
|---|---|---|---|
| [[wiki/frida/_index|Frida]] | Scripting, Stalker, Interceptor, CodeWriters | N | YYYY-MM-DD |
| [[wiki/obfuscation/_index|Obfuscation]] | O-LLVM, control-flow flattening, string encryption | N | YYYY-MM-DD |
| [[wiki/rasp/_index|RASP]] | Anti-root, integrity checks, anti-debug | N | YYYY-MM-DD |
| [[wiki/apk/_index|APK Analysis]] | APK fingerprints, protection detection, analysis records | N | YYYY-MM-DD |
| [[wiki/techniques/_index|Techniques]] | Reusable unpacking/analysis techniques with evidence | N | YYYY-MM-DD |
| [[wiki/experiments/_index|Experiments]] | Experiment records (success, partial, failure) | N | YYYY-MM-DD |
| [[wiki/success-traces/_index|Success Traces]] | Verified successful workflows with causality analysis | N | YYYY-MM-DD |
| [[wiki/packers/_index|Packers]] | Packer name → verified unpacking method (primary reuse artifact) | N | YYYY-MM-DD |
| [[wiki/tool-registry/_index|Tool Registry]] | Available tools with capabilities and install guidance | N | YYYY-MM-DD |
| [[wiki/patterns/_index|Patterns]] | Protection patterns with indicators and technique links | N | YYYY-MM-DD |
| [[wiki/knowledge-diffs/_index|Knowledge Diffs]] | Knowledge base changes after each analysis | N | YYYY-MM-DD |
```

---

## 2. Topic `_index.md` — Per-Folder Navigation

```markdown
# <Topic Name> — Index

## Quick Navigation
<!-- Routing decision tree based on LLM query -->
Looking for... → Go to...
- "How do I hook a Java method?" → [[frida-interceptor]]
- "How do I trace all calls in a module?" → [[frida-stalker]]

## Articles
| Article | Covers (Summary) | Type | Completeness | Last updated |
|---|---|---|---|---|
| [[frida-interceptor]] | <llm_summary from YAML> | api-doc | complete | YYYY-MM-DD |
```

---

## 3. Cross-Topic Indexes

Note: Build these dynamically by parsing the YAML frontmatter of all articles during `reindex`.

### `_tools-index.md`
```markdown
| Tool | Tested version | Key articles | Notes |
|---|---|---|---|
| Frida | 16.2 | [[wiki/frida/...]] | 16.x behavior differs from 15.x |
```

### `_snippets-index.md`
```markdown
| Purpose | Language | Tool | Article | Tags |
|---|---|---|---|---|
| Bypass OkHttp3 pinning | JS | Frida 16.x | [[wiki/rasp/...]] | #ssl #okhttp |
```

### `_patterns-index.md`
```markdown
| Pattern | Type | Targets seen | Articles | First filed |
|---|---|---|---|---|
| DexGuard v4.x XOR string decrypt | Obfuscation | 4 | [[wiki/obfuscation/...]] | YYYY-MM-DD |
```

### `_ttp-index.md`
```markdown
| TTP ID | Name | Tactic | Articles | Notes |
|---|---|---|---|---|
| T1629.003 | Disable/Modify Tools | Defense Evasion | [[wiki/rasp/...]] | anti-Frida patterns |
```

### `_apk-index.md`
```markdown
| APK SHA256 | Package | Version | Protections | Analysis Status | Bypass Status |
|---|---|---|---|---|---|
| <hash> | com.example.app | 1.0.0 | [packer, anti-debug] | complete | partial |
```

### `_technique-index.md`
```markdown
| Technique ID | Name | Category | Promotion State | Confidence | Applicable Patterns |
|---|---|---|---|---|---|
| T-XXXX | <name> | unpacking | VALIDATED | 0.75 | [P-XXXX, P-YYYY] |
```

### `_experiment-index.md`
```markdown
| Experiment ID | Analysis | Technique | Result | Verification | Key Learning |
|---|---|---|---|---|---|
| EXP-XXXX | A-XXXXXX | T-XXXX | SUCCESS | VERIFIED_SUCCESS | <learning> |
```

### `_packer-index.md`
```markdown
| Packer ID | Name | Unpacking Status | Confidence | First Indicator | Techniques |
|---|---|---|---|---|---|
| 360-jiagu | 360 jiagu (PokeGuard-style variant) | unpacked | 0.9 | com.qihoo.util.* stub classes | [T-0016, T-0017, T-0018, T-0019] |
```

### `_tool-registry-index.md`
```markdown
| Tool ID | Name | Version | Category | Host/Device | Availability | Key Capabilities |
|---|---|---|---|---|---|---|
| TR-XXXX | Frida | 16.2 | dynamic-observation | both | available | [hook, trace, dump] |
```

### `_pattern-index.md`
```markdown
| Pattern ID | Name | Category | Protection Type | Confidence | Techniques |
|---|---|---|---|---|---|
| P-XXXX | DexProtector 5.x | packer | DexProtector | 0.85 | [T-XXXX, T-YYYY] |
```

### `_knowledge-diff-index.md`
```markdown
| Diff ID | Analysis | Timestamp | New Techniques | Updated Techniques | Confidence Changes |
|---|---|---|---|---|---|
| KD-XXXX | A-XXXXXX | YYYY-MM-DD | [T-XXXX] | [T-YYYY] | T-ZZZZ: 0.61→0.74 |
```

---

## Index Maintenance Rules

- **Every article** must appear in its topic's `_index.md` and at least one cross-topic index.
- **Link format:** Use simple relative Obsidian links, e.g., `[[wiki/topic/article-name]]` or `[[article-name]]` if within the same directory. Do not use absolute repository paths.
- **YAML Extraction:** When updating tables, pull information directly from the article's YAML block (especially `llm_summary`, `tool_versions`, and `type`).
- **Article count** and **last updated** fields must be refreshed on every index update.
- **Graph Visualizer:** After index updates, the compile pipeline auto-runs `python3 .kb/scripts/graph_generator.py` to regenerate `knowledge_base/graph/graph_data.js`.

