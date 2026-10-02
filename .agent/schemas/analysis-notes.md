# Schema: Personal RE Notes / Analysis Notes

> **Use when:** Source is first-person, contains observations, hypothesis language.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)

---

## Template

```markdown
---
type: analysis-notes
topic: wiki/<topic>/_index
source: <filename or "personal notes">
tags: [tag1, tag2]
complexity: intermediate | advanced
completeness: stub | partial | complete
last_verified: YYYY-MM-DD
tool_versions: [<if applicable>]
target: <package name or binary — redact if sensitive>
analysis_date: YYYY-MM-DD
status: in-progress | complete | abandoned
bypass_status: complete | partial | failed | not-attempted
llm_summary: "<A dense, 1-2 sentence summary of the analysis findings and conclusions for direct LLM retrieval>"
---

# <Target Description or Topic> — Analysis Notes

## This Article Answers
- "What did analysis of <target/topic> reveal?"
- "What techniques were tried on <protection type>?"

## Key Takeaways
- [VERIFIED] <confirmed finding>
- [DEAD-END] <approach that definitively failed + why>
- [HYPOTHESIS] <unconfirmed theory worth following up>

## Verified Observations [V]
<!-- Only what you directly confirmed. One claim per bullet. -->
- <observation>

## Hypotheses [I/U]
<!-- Educated guesses. Clearly labeled. -->
- <hypothesis — why you think this>

## Dead Ends
<!-- Critical section — prevents repeating failed work -->
| Approach | Why it failed | Confidence in failure |
|---|---|---|
| <approach> | <reason> | High / Medium |

## Working Techniques
```<language>
// snippet that worked
```
> **Context:** <exactly when and why this worked>
> **Caveats:** <conditions, versions>

## Open Questions
- <what remains unknown or untested>

## Related
- [[wiki/patterns/<pattern>]] — matched pattern if any
- [[wiki/techniques/<technique>]] — technique applied
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `target` | Yes | Package name, binary name, or target topic |
| `analysis_date` | Yes | Date analysis was conducted (YYYY-MM-DD) |
| `status` | Yes | `in-progress` / `complete` / `abandoned` |
| `bypass_status` | Yes | `complete` / `partial` / `failed` / `not-attempted` — critical for target routing |

### Content Rules
- **Dead Ends is the most valuable section** — it prevents repeating failed work across sessions
- Clearly separate `[V]` verified observations from `[I/U]` hypotheses — never mix
- Redact sensitive target names if needed, but keep package identifiers for cross-referencing

