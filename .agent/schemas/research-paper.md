# Schema: Research Paper

> **Use when:** Source has abstract, citations, methodology section, or DOI.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)

---

## Template

```markdown
---
type: research-paper
topic: wiki/<topic>/_index
source: <URL or DOI>
tags: [tag1, tag2]
complexity: intermediate | advanced
completeness: stub | partial | complete
last_verified: YYYY-MM-DD
tool_versions: [<if applicable>]
authors: [<Last, First et al.>]
published: <Venue, Year>
doi_url: <link>
llm_summary: "<A dense, 1-2 sentence summary of the paper's core findings and its practical applicability to Reverse Engineering for direct LLM retrieval>"
---

# <Paper Title>

## This Article Answers
- "<exact question this paper answers>"
- "<second question>"
- NOT: "<related question this does NOT answer → see [[wiki/other/article]]>"

## Key Takeaways
<!-- Self-contained. Must answer 80% of queries without reading further. -->
- [FINDING] <core result, one line>
- [FINDING] <second result>
- [LIMITATION] <most important limitation>
- [RE-APPLICABILITY] <how this applies to Android RE work specifically>

## Problem Statement
- What gap does this paper address? [V]
- Why existing approaches fail [V]

## Methodology
- Approach used [V]
- Dataset / targets / environment [V]
- Key tools or frameworks built [V]

## Key Findings
- <Finding with inline citation marker> [V]
- <Finding> [V]
- Note: multi-claim sentences should be broken into one claim per bullet

## Limitations Stated by Authors
- [V] <limitation directly stated in paper>

## RE Applicability
<!-- Most important section for this KB. -->
- How to apply this to Android RE work [I]
- Which wiki topics this informs: [[wiki/topic/article]]
- Techniques or tools proposed that are usable now [V/I]

## What This Article Does NOT Cover
- <explicit scope boundary>

## Open Questions / Unverified Claims
- <claim from paper that needs independent verification>
- <conflicting data with another source>

## Related
- [[wiki/topic/article]] — reason for link
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `authors` | Yes | YAML array of author names (Last, First et al.) |
| `published` | Yes | Venue and year (e.g., "USENIX Security, 2024") |
| `doi_url` | Conditional | Required if the paper has a DOI. Omit if preprint only. |

### Content Rules
- **RE Applicability is the most important section** — this is what makes the paper useful in this KB
- Break multi-claim sentences into one claim per bullet
- Use `[V]` for claims directly from the paper; use `[I]` for your interpretation of applicability
- If paper is behind paywall, note in Source field and mark claims from abstract-only as `[U]`

