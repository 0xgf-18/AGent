# WRITE MODE — Compile Pipeline

> **Load when:** `compile` command. **Prerequisite:** `core-rules.md`
> **See also:** [schemas/](schemas/) | [index-formats.md](index-formats.md)

---

## 1. Content Type Router

Classify the raw file, then load the matching schema from `.kb/schemas/`.

| Priority | Type | Signals | Schema |
|---|---|---|---|
| 1 | Pentest finding | CVSS, finding title, recommendation | `pentest-finding.md` |
| 2 | Malware analysis | IOC tables, family name, C2 | `malware-analysis.md` |
| 3 | Research paper | Abstract, citations, DOI | `research-paper.md` |
| 4 | API / SDK doc | Function signatures, param tables | `api-reference.md` |
| 5 | Analysis notes | First-person, hypothesis language | `analysis-notes.md` |
| 6 | Blog / writeup | Narrative walkthrough, dated | `blog-writeup.md` |

**Tiebreaker:** Highest priority wins. If the file covers two distinct domains, split per §3 and assign each chunk its own schema. Multi-topic files (3+ distinct `##` domains) → split per §3 first.

---

## 2. Compile Steps

**ZERO-LOSS DIRECTIVE:** Never summarize. Preserve ALL offsets, hex, registers, paths, syscalls, bypass scripts, and code verbatim.

1. **Read** entire raw file. **List all `##` headings and code blocks** as a coverage checklist.
2. **Images:** Process per §4. Extract text before writing.
3. **Classify** → select schema (§1).
4. **Pre-flight plan:** List chunks, hub file, and indexes to update.
5. **Load schema** from `.kb/schemas/<type>.md`.
6. **YAML metadata:** Hub vs chunk rules in §3. Dense 1-2 sentence `llm_summary`.
7. **Write articles** per schema. Check off headings/code from step 1 as you write. Updates → §5.
8. **Update** topic `_index.md` + cross-topic indexes (→ `index-formats.md`).
9. **Cross-link** every new article from ≥1 existing article.
10. **Link verification:** Check all `[[wiki links]]` resolve. Stub missing targets.
11. **Coverage check** (DO NOT re-read raw): confirm every `##` heading and code block is in a chunk.
12. **Rename** raw file: append `_processed`.
13. **Graph:** `python3 .kb/scripts/graph_generator.py`
14. **Log** to `knowledge_base/wiki/log.md`:
```markdown
## [YYYY-MM-DD] compile | <source>
- Type: <type> | Articles created: <list> | Updated: <list>
- Indexes updated: <list> | Graph: yes
- Markers: [V]×N [U]×N [I]×N | Open questions: N
```

---

## 3. Splitting & Navigation

**MANDATORY:** Deep-dive articles MUST split into Hub + semantic chunks.

> The split unit is a **technical mechanism**, NOT a product/target name.
> DexProtector, SingPass, r2-pay are containers — the mechanisms inside are the chunks.

**Split when:** 2+ distinct protection mechanisms, or 3+ distinct `##` technical areas.
**Single article OK:** Exactly ONE mechanism in depth, or an API reference chunk.

### Directory Layout
```
wiki/<topic>/<subject>/
├── _hub.md              ← LLM decision router
├── hook-prologue.md     ← Chunk: mechanism name only, no subject prefix
├── anti-debug.md
└── ...
```
Chunk filenames = mechanism only. Links: `[[wiki/<topic>/<subject>/hook-prologue]]`

### Hub vs Chunk YAML

**Hub** carries shared metadata: `type`, `topic`, `source`, `tags`, `complexity`, `completeness`, `last_verified`, `tool_versions`, `author`, `published`, `reproducibility`, `llm_summary`.

**Chunks** carry minimal: `type`, `topic`, `source`, `tags`, `complexity`, `llm_summary`.

### Procedure
1. List all mechanisms → each is a chunk candidate.
2. One chunk per mechanism. Never merge mechanisms.
3. Navigation at top of each chunk:
   ```markdown
   [Hub]([[wiki/<topic>/<subject>/_hub]]) | [Prev](...) | [Next](...)
   ```
4. Per chunk: verbatim code in fenced blocks, bullets over prose, deep headers (`###`/`####`).
5. Hub = decision router with 2-3 sentence summary per chunk.
6. Add Hub to `_master-index.md` + topic `_index.md`. Add chunks to topic `_index.md`.

---

## 4. Image Handling

**Transcribe verbatim. Never summarize.** Images in `knowledge_base/raw/assets/<article>/<image>.<ext>`.

| Category | Action |
|---|---|
| `DISASSEMBLY` | Transcribe ALL instructions verbatim. Function name, addresses, symbols. |
| `DECOMPILED_CODE` | Transcribe CODE verbatim. Class + method. Flag: crypto, JNI, integrity. |
| `TOOL_OUTPUT` | Transcribe EVERY line verbatim. |
| `DIAGRAM` | Components, flow (`A → B → C`), security boundaries, all labels. |
| `HEX_DUMP` | Transcribe HEX verbatim with offsets and ASCII. |
| `SCREENSHOT` | Transcribe ALL text, versions, errors verbatim. |
| `DECORATIVE` | Skip. Write `> **[Image: decorative — skipped]**` |

Insert as: `> **[Image extracted — CATEGORY | confidence: high/low]**` + extracted content.
Low confidence: append `— verify against original source: <url>`.

---

## 5. Update Protocol

When new source overlaps an existing article:

1. **Diff** → identify genuinely new details.
2. **Merge inline** into existing sections. Tag: `[V: <new-source>]`.
3. **Contradictions** → `[X: see <article>]` on both claims. Add to Open Questions. Prefer higher-quality source per `core-rules.md` §2.3.
4. **Update YAML:** `last_verified`, `completeness`, add new `source`.
5. **Never create "Part 2"** — merge over proliferation.
