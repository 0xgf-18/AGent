# READ MODE — Query Protocol

> **Scope:** How to navigate the KB and answer questions.
> **Load when:** User or consuming agent queries the KB.
> **Prerequisite:** Read `core-rules.md` first.
> **See also:** [core-rules.md](core-rules.md) | [index-formats.md](index-formats.md)

---

## Direct Markdown Traversal Steps

Follow this protocol when retrieving information from the KB:

### Step 1 — Route via Master Index
```
Read knowledge_base/wiki/_master-index.md
→ Scan the Quick Navigation list or Topic Index table
→ Identify the relevant topic folder (e.g. wiki/rasp/ or wiki/obfuscation/)
→ If the query lies outside documented topics, state "not in KB" immediately
```

### Step 2 — Navigate Topic Index
```
Read wiki/<topic>/_index.md
→ Read the "Quick Navigation" decision tree to find specific articles
→ If the target is not listed in this topic, stop and check other indices
```

### Step 3 — Read YAML Metadata & Content
```
Read the specific article markdown file
→ Verify tool_versions and llm_summary in the YAML frontmatter first
→ Read Key Takeaways and Walkthrough sections
→ If the article is part of a hub+chunk series, check the hub for related chunks
```

### Step 4 — Compose Single Consolidated Technical Response

Compose **ONE seamless, highly granular technical document**. High-level abstract summaries are strictly forbidden. Every mechanism must be explained down to its exact function names, assembly opcodes, register operations, C/C++ structures, or JNI signatures.

#### Mandatory Formatting Rules:
1. **NO Separate Section Headers:** DO NOT output separate section headers like `## 📚 Knowledge Base Findings` or `## 🧠 AI Intelligence & Analysis`.
2. **Deep Technical Granularity:** Include exact function names (`rtld_db_dlactivity`), opcodes (`sub sp, sp, #0x30`), structs (`DT_ANDROID_RELA`), and code snippets. Show **HOW** it works, not just high-level descriptions.
3. **Inline Provenance Markers:** Use the claim marker system from `core-rules.md` §2.1. Tag every sentence and code block inline with its source marker (`[V]`, `[I]`, `[U]`, `[VS]`, `[X]`, `[AI Synthesis]`).

#### Example Response:
```markdown
# DexProtector (Licel 5.x) Detection & Anti-Analysis Architecture

### 1. Implicit Linker-State Anti-Frida (`rtld_db_dlactivity`)
DexProtector binds stage 2 (`libdp.so`) decryption directly to the execution bytes of the dynamic linker function `rtld_db_dlactivity()`. [[wiki/protectors/dexprotector-bootstrap]] [V] 

When `frida-server` attaches, it writes an ARM64 trampoline at `rtld_db_dlactivity()`: [AI Synthesis]

```assembly
; [AI Synthesis] Standard Frida Linker Trampoline
ldr x16, #0x8
br  x16
.quad <frida_handler_address>
```

Because stage 2 key derivation reads bytes from `rtld_db_dlactivity()`, running Frida corrupts the key state, causing `libdp.so` payload decryption to fail with a memory fault. [[wiki/protectors/dexprotector-bootstrap]] [V]

To bypass this check, restore the original `ret` opcode (`0xd65f03c0`) before key derivation executes: [AI Synthesis]

```javascript
// [AI Synthesis] Linker Byte Restoration Pattern
Memory.protect(Module.getExportByName(null, 'rtld_db_dlactivity'), 4, 'rwx');
Module.getExportByName(null, 'rtld_db_dlactivity').writeByteArray([0xc0, 0x03, 0x5f, 0xd6]);
```
```

---

## When the KB Has Partial or No Information

If a query is not fully covered by any wiki article:

1. State clearly what is missing from the local KB (e.g., *"Not currently documented in local wiki"`).
2. Provide the full technical solution inline, marking all model-generated claims and code blocks as `[AI Synthesis]`.
3. Offer to compile a new raw KB article from the AI response so it can be saved into the KB inbox!
