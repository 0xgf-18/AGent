# Schema: Blog Post / Writeup / Tutorial

> **Use when:** Source is a narrative walkthrough, dated, with author byline.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)

---

## Template

```markdown
---
type: blog
topic: wiki/<topic>/_index
source: <URL>
tags: [tag1, tag2]
complexity: beginner | intermediate | advanced
completeness: stub | partial | complete
last_verified: YYYY-MM-DD
tool_versions: [<if applicable>]
author: <name or handle>
published: YYYY-MM-DD
reproducibility: verified-by-me | unverified | likely-outdated
llm_summary: "<A dense, 1-2 sentence summary of the article's technique and core steps for direct LLM retrieval>"
---

# <Title>

[Hub]([[wiki/<topic>/<hub-name>]]) | [Prev]([[wiki/<topic>/<prev>]]) | [Next]([[wiki/<topic>/<next>]])
*(Remove Navigation line if this is a standalone article)*

## This Article Answers
- "<question>"
- NOT: "<out-of-scope question → see [[wiki/other]]>"

## Key Takeaways
- [TECHNIQUE] <core technique in one line>
- [PREREQ] <what you need before using this>
- [GOTCHA] <most important thing that breaks>
- Reproducibility: <verified-by-me | unverified | likely-outdated>

## Low-Level Technical Invariants [V]
<!-- Use this section to capture exact binary, memory, network and filesystem indicators. DO NOT summarize hex/offsets. -->
| Target / Metric | Attribute | Value / Details | Notes |
|---|---|---|---|
| Memory Offset | `0x100E4CF38` | Base check comparison | e.g. Address of comparison |
| Hex / Constant | `0x3a5b6c7d` | Expected MurmurHash32 | e.g. Pre-calculated hash value |
| Registers | `X11` / `X12` | Double registers check | e.g. Register optimization trick |
| System call | `openat` / `read` | `/proc/self/status` | e.g. Byte-per-byte read call |
| File / Directory | `/sys/class/` | Path check for root | e.g. RootBeer check path |

## Prerequisites
- Environment required [V]
- Tools and versions [V][VS: <version>]
- Knowledge assumed [V]

## Technique Summary
- What the technique accomplishes [V]
- When it applies [V]
- When it does NOT apply [V]

## In-Depth Walkthrough
<!-- DO NOT CONDENSE. Convert narrative into dense bullet points preserving 100% of technical specifics. -->
- **Step 1: <Action>**
  - Technical detail 1
  - Technical detail 2
- **Step 2: <Action>**

## Known Bypass & Mitigation Vectors
<!-- List how the check was successfully defeated or patched. -->
### Vector 1: <Name of Bypass, e.g. Frida Runtime Hooking>
```javascript
// Complete, runnable snippet
```
*   **Target point:** <Hooked method signature or memory offset>
*   **Result:** <Expected behaviour and register/argument manipulations>

### Vector 2: <Name of Bypass, e.g. Static Assembly Patching>
*   **Target Offset:** `0x100E4CF38`
*   **Original Instruction:** `B.NE loc_crash`
*   **Patched Instruction:** `NOP` or `B loc_safe`
*   **Notes:** <Any instruction length or CRC checksum concerns>

## Code Snippets

```<language>
// verbatim from source
```
> **Context:** <what this does and when to use it>
> **Caveats:** <what breaks, version notes>
> **Tested on:** <tool version, Android version, arch>
> **Source line:** [V] or [U]

## Gotchas
- <thing that silently fails> [V/U]
- <version-specific behavior> [VS: x.x]

## What This Article Does NOT Cover
- <scope boundary>

## Open Questions / Unverified Claims
- <blog claim that needs verification>

## Related
- [[wiki/topic/article]] — reason
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `author` | Yes | Author name or handle from the blog post |
| `published` | Yes | Original publication date (YYYY-MM-DD) |
| `reproducibility` | Yes | `verified-by-me` / `unverified` / `likely-outdated` — helps LLM assess reliability |

### Content Rules
- **Low-Level Invariants Table is Mandatory:** Any binary offset, checksum, register configuration, system call number, or file path must be logged exactly.
- **Bypass & Mitigation Vectors Section is Mandatory:** You must document how the check was defeated (via hooking, patching, or filesystem manipulation).
- **Date is critical** — blogs age. A 2019 Frida post may not work with Frida 16.x
- **Preserve Depth** — Do not condense steps. Extract the full technical details.
- Code snippets must be verbatim from source, never paraphrased
- Every code block needs the `Context / Caveats / Tested on` annotation

