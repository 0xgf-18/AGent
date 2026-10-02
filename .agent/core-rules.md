# Core Rules & Anti-Hallucination System

> **Scope:** Behavioral rules that apply to EVERY KB operation.
> **Load:** Always — this file is mandatory for all modes.
> **See also:** [read-protocol.md](read-protocol.md) | [write-pipeline.md](write-pipeline.md)

---

## 1. Behavioral Rules

- **You own `knowledge_base/wiki/`.** User rarely edits wiki files directly.
- **`knowledge_base/raw/` is the inbox.** Process raw notes/blogs via the compile pipeline (→ `write-pipeline.md`).
- **YAML Frontmatter:** Every article MUST start with a YAML metadata block containing required common and schema-specific fields.
- **No orphans:** Every article must be listed in its topic's `_index.md` and linked from at least one other article.
- **No paraphrasing code:** Function names, offsets, opcodes, and JNI signatures must be kept verbatim from the source.
- **Image Handling & Inlining:** Transcribe image text, assembly instructions, or diagram flows where accessible. Preserve image links with captions/alt-text when pixel data is unreadable in the runner.
- **Version-pin everything:** Tool and SDK versions (e.g. Frida 16.x vs 15.x, Android 13 vs 14) must be explicitly pinned.
- **Unified Granular Responses:** In query/search mode, output ONE seamless, highly granular technical document containing exact opcodes, function names, C/assembly snippets, and IPC structures. Inline model intelligence (`[AI Synthesis]`) directly alongside KB verified facts (`[V]` / `[[wiki/...]]`). NEVER output separate section headers like "Knowledge Base Findings" vs "AI Intelligence & Analysis", and NEVER provide abstract high-level summaries.
- **Auto-Graph on compile:** Automatically run `python3 .kb/scripts/graph_generator.py` after any `compile` operation to keep the Knowledge Graph Visualizer synchronized.

---

## 2. Anti-Hallucination System

Every factual claim in a wiki article must carry a provenance marker to prevent consuming LLMs from confabulating when traversing the KB.

### 2.1 Inline Claim Markers

Append to any sentence containing a factual claim:

| Marker | Meaning |
|---|---|
| `[V]` | Verified — directly confirmed from the cited primary source |
| `[I]` | Inferred — logical conclusion from verified facts, not explicitly stated |
| `[U]` | Unverified — from blog/forum/secondary source, not independently confirmed |
| `[VS: Frida 16.x]` | Version-specific — only applies to stated version/environment |
| `[X: see <article>]` | Contradicted — conflicts with another article; check both |
| `[AI Synthesis]` | AI Model Intelligence — general pre-trained reasoning, code patterns, or context |

**Example:**
```markdown
Frida Stalker uses a code cache of 512KB per thread by default. [V]
Increasing this may reduce tracing overhead on heavy targets. [I]
To bypass this check, attach a script before thread initialization: [AI Synthesis]
```

### 2.2 Mandatory Uncertainty Sections

Every wiki article must include these two sections to enforce clear boundaries for consuming LLMs:

```markdown
## What This Article Does NOT Cover
- <explicit scope boundary — prevents LLM from over-extending this article>
- e.g., "iOS-specific Frida behavior — see [[wiki/frida/frida-ios]]"
- e.g., "Frida versions before 16.x — behavior may differ"

## Open Questions / Unverified Claims
- <claims encountered in source that couldn't be verified>
- <conflicting information from multiple sources>
```

### 2.3 Source Quality Hierarchy

When multiple sources cover the same topic, prefer in this order:
1. Primary source (Frida official docs, Android AOSP, IEEE/USENIX paper)
2. Vendor security blog (Google Project Zero, NCC Group, Synacktiv)
3. Practitioner blog (verified technique, dated)
4. Forum / community post (treat as [U] until verified)

When sources conflict: document both, mark the lower-quality source `[U]`, and add to Open Questions.

---

## 3. Hard Rules for Querying

- If a query touches something not in the KB, state: *"This is not in the local KB. I can answer from general training knowledge but cannot verify against local sources."*
- Never silently blend KB facts and training data priors.
- Always surface `[U]`, `[VS]`, and `[X]` markers when they appear in the source files.
