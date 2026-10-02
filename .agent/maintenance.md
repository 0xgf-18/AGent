# KB Maintenance — Health Check, Commands, Logging

> **Scope:** Health checks, hygiene commands, and operational logging.
> **Load when:** User triggers `health-check`, `gap report`, or `contradictions`.
> **See also:** [index-formats.md](index-formats.md)

---

## 1. Health Check

Run on command `health-check`. Scans the entire KB for structural issues. Report results directly to the user.

### Check List
1. **Dead `[[wiki links]]`**: Grep all markdown files for `[[...]]` links and verify each target file exists.
2. **Orphan Articles**: Articles that are not linked from any topic `_index.md` or other wiki articles.
3. **YAML Frontmatter Validation**: Check every article for required fields defined in `schemas/_common-metadata.md`: `type`, `topic`, `source`, `tags`, `complexity`, `completeness`, `last_verified`, `llm_summary`.
4. **Stale stubs**: Articles with `completeness: stub` not updated in >14 days.
5. **Unprocessed raw files**: Files in `knowledge_base/raw/feeds/` without `_processed` suffix.

---

## 2. Specialized Commands

| Command | Action |
|---|---|
| `health-check` | Run the full check list (§1 above). |
| `gap report` | Report dead links, stale stubs, and underdeveloped topics (<2 articles). |
| `contradictions` | List all articles carrying `[X]` conflict markers. |

---

## 3. `log.md` Format

Append-only. Never edit past entries.

```markdown
## [YYYY-MM-DD] <command> | <target or source>
- Result: <summary>
- Articles created: <list>
- Articles updated: <list>
- Claim markers: [V]×N [I]×N [U]×N
- Open questions filed: N
- New patterns: <list or none>
```
