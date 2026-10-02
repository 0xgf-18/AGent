# Schema: API / SDK Reference & Usage Patterns

> **Use when:** Source has function signatures, parameter tables, or version header.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)
> **Note:** Reference signatures and usage patterns are consolidated into this single file to optimize for direct markdown traversal by consuming agents.

---

## Template

```markdown
---
type: api-doc
topic: wiki/<topic>/_index
source: <URL>
tags: [tag1, tag2]
complexity: intermediate | advanced
completeness: stub | partial | complete
last_verified: YYYY-MM-DD
tool_versions: [<tool x.x>]
sdk_library_version: <x.x.x>
official_source: <URL>
llm_summary: "<A dense summary of the API class, its core purpose, and target use case for direct LLM retrieval>"
---

# <API or SDK Name> — Reference & Usage Patterns

## 1. Class Purpose & Core Use Cases
*   **Purpose:** <What this library/class does in 1 sentence - e.g. 'Used to dynamically construct AArch64 machine instructions at runtime.'> [V]
*   **Primary RE Use Case:** <e.g., 'Dynamically patching native JNI methods to skip check gates.'> [V]
*   **When to Use:** Use this class when <condition, e.g. 'you need to compile memory instructions directly without writing raw shellcode bytes.'> [I]
*   **When NOT to Use:** Do not use if <condition, e.g. 'targeting ARM32 or x86 architectures; use ArmWriter or X86Writer instead.'> [VS: AArch64]

## 2. Selection Guide
| Target Architecture / Scenario | Use This API Class | Instead of | Why |
|---|---|---|---|
| AArch64 (64-bit ARM) | Arm64Writer | ArmWriter | Native 64-bit instruction generation |

---

## 3. API Signatures & Behaviors

### <Method / Function Name>

```<language>
// Exact signature verbatim from source
methodName(param: Type): ReturnType
```
*   **Parameters:**
    *   `param`: <Description and expected value type>
*   **Return Value:** <Detailed return behavior under success and failure conditions>
*   **Under-the-Hood Behavior:** <Non-obvious side-effects, memory locks, thread implications> [V]
*   **Version discrepancy:** <if behavior changed across versions> [VS: x.x]

<!-- Duplicate block per logical API method group -->

---

## 4. Complete Usage Patterns & Code Walkthroughs

### Pattern 1: <Name of Task, e.g. Hooking and Spoofing Return Values>
```javascript
// Complete, runnable code snippet demonstrating the API usage
```

#### Selection & Context:
*   **Goal:** <What task this code snippet accomplishes>
*   **When to Use:** <Exact scenario, e.g. 'Use this code block if the target library uses dlopen to load JNI libraries late.'>
*   **Tested Environment:** <Versions of tools, OS, and Architecture>

#### How the Code Works (Step-by-Step):
1.  **Line 1-3:** <Description, e.g. 'Attaches an Interceptor to the native open symbol.'>
2.  **Line 5:** <Description, e.g. 'Reads the pointer to the filename argument from register X0.'>
3.  **Line 7-9:** <Description, e.g. 'Spoofs the return code to 0 if the filename matches our target.'>

#### Gotchas & Silent Failures:
*   <silently fails if X condition is met> [V]
*   <known version discrepancy> [VS: x.x]

---

## 5. Gotchas & Silent Failures (General)
- <silent failure condition> [V]
- <version difference> [VS: x.x]
- <common mistake + symptom> [V/U]

## 6. What This Article Does NOT Cover
- <scope boundary>

## 7. Open Questions / Unverified Claims
- <undocumented behavior observed but not confirmed>

## 8. Related
- [[wiki/topic/article]] — reason
```

---

## Key Rules for This Schema

- **Signatures + Patterns Stay Together:** Within each article (or semantic chunk), reference signatures and their usage patterns must coexist. Never split signatures into a separate companion `-patterns.md` file.
- **Semantic Chunking Allowed:** If the raw source covers multiple API domains (e.g., Interceptor, Stalker, Memory), apply write-pipeline §3 semantic chunking. Each chunk becomes a self-contained API reference for that domain.
- **Mandatory Walkthroughs:** For every code pattern, provide a numbered step-by-step description under "How the Code Works".
- **Selection Guides:** Must help the LLM select the correct API variant without reading full docs.
- **Signatures Verbatim:** Parameter names, types, and return values must be verbatim from official source docs.

