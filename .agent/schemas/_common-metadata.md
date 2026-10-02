# Common Article Metadata (YAML Frontmatter)

> **Scope:** Shared metadata fields used by ALL article schemas.
> **Usage:** Include this block at the very top of every wiki article (delimited by `---`).

---

## Metadata Block Template

```yaml
---
type: <schema type>
topic: wiki/<topic>/_index
source: <URL, DOI, or filename>
tags: [tag1, tag2]
complexity: beginner | intermediate | advanced
completeness: stub | partial | complete
last_verified: YYYY-MM-DD
tool_versions: [Frida x.x, Android x, IDA x.x]
llm_summary: "<A dense, 1-2 sentence summary of the article's core knowledge for direct LLM indexing/retrieval>"
---
```

## Field Rules

| Field | Required | Notes |
|---|---|---|
| type | Yes | Must match one of: `research-paper`, `blog`, `api-doc`, `pentest-finding`, `analysis-notes`, `malware-analysis` |
| topic | Yes | Relative path to the parent topic `_index.md` (e.g. `wiki/rasp/_index`) |
| source | Yes | Original URL, DOI, or raw filename. Never omit. |
| tags | Yes | YAML array of lowercase, hyphenated tags. Min 2, max 8. |
| complexity | Yes | beginner | intermediate | advanced |
| completeness | Yes | `stub` = placeholder, `partial` = key sections done, `complete` = fully populated |
| last_verified | Yes | Date this article was last checked against its source (YYYY-MM-DD) |
| tool_versions | Conditional | YAML array of version strings. Required if article mentions versioned tools. |
| llm_summary | Yes | A dense, 1-2 sentence summary of the article content for direct LLM search and navigation. |
