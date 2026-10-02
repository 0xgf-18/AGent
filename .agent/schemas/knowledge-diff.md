# Schema: Knowledge Diff

> **Use when:** Recording changes to the knowledge base after an analysis completes.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)
> **Generated automatically** after each analysis — makes learning transparent.

---

## Template

```markdown
---
type: knowledge-diff
topic: wiki/knowledge-diffs/_index
source: <analysis_id>
tags: [tag1, tag2]
complexity: beginner
completeness: complete
last_verified: YYYY-MM-DD
tool_versions: []
diff_id: <KD-XXXX>
analysis_id: <A-XXXXXX>
timestamp: YYYY-MM-DDTHH:MM:SS
trigger: analysis-complete | experiment-complete | technique-updated | manual
llm_summary: "<A dense, 1-2 sentence summary of what changed in the knowledge base for direct LLM retrieval>"
---

# Knowledge Diff KD-XXXX

## This Article Answers
- "What changed in the knowledge base after analysis A-XXXXXX?"
- "What new techniques were learned?"
- "What confidence levels were updated?"

## Key Takeaways
- [NEW] <count> new techniques/patterns
- [UPDATED] <count> updated techniques
- [CONFIDENCE] <count> confidence changes
- [RELATIONSHIPS] <count> new relationships

## Summary
**Analysis:** A-XXXXXX
**Timestamp:** YYYY-MM-DDTHH:MM:SS
**Trigger:** analysis-complete
**Overall Impact:** LOW / MEDIUM / HIGH

## NEW Entries
### Techniques
| Technique ID | Name | Category | Confidence | Source |
|---|---|---|---|---|
| T-XXXX | `<name>` | `<category>` | 0.XX | EXP-XXXX |

### Patterns
| Pattern ID | Name | Category | Confidence | Source |
|---|---|---|---|---|
| P-XXXX | `<name>` | `<category>` | 0.XX | A-XXXXXX |

### Success Traces
| Trace ID | Analysis | Experiment | Verification |
|---|---|---|---|
| ST-XXXX | A-XXXXXX | EXP-XXXX | VERIFIED_SUCCESS |

### Experiments
| Experiment ID | Analysis | Result | Verification |
|---|---|---|---|
| EXP-XXXX | A-XXXXXX | SUCCESS/FAIL | VERIFIED/UNVERIFIED |

## UPDATED Entries
### Techniques
| Technique ID | Previous Version | New Version | Change Type | Reason |
|---|---|---|---|---|
| T-XXXX | v1 | v2 | workflow/update/confidence/limitation | `<reason>` |

### Patterns
| Pattern ID | Change Type | Details |
|---|---|---|
| P-XXXX | indicators/techniques/confidence | `<details>` |

## CONFIDENCE CHANGES
| Technique ID | Previous | New | Delta | Reason |
|---|---|---|---|---|
| T-XXXX | 0.XX | 0.YY | +0.ZZ / -0.ZZ | `<reason: reproduced/failed/refined>` |

## NEW FAILURES
| Technique ID | Condition | Analysis | Impact |
|---|---|---|---|
| T-XXXX | `<condition>` | A-XXXXXX | reduced applicability |

## NEW RELATIONSHIPS
| From | To | Type | Evidence |
|---|---|---|---|
| Pattern P-XXXX | Technique T-XXXX | addresses | A-XXXXXX |
| Technique T-XXXX | Tool TR-XXXX | requires | EXP-XXXX |
| Technique T-XXXX | Environment env-XXXX | requires | EXP-XXXX |
| APK A-XXXXXX | Pattern P-XXXX | matches | detection |

## DEPRECATED/ARCHIVED
| Entry ID | Type | Reason |
|---|---|---|
| `<id>` | technique/pattern | `<reason>` |

## METRICS
| Metric | Before | After | Delta |
|---|---|---|---|
| Total Techniques | N | N | +N |
| Validated Techniques | N | N | +N |
| Trusted Techniques | N | N | +N |
| Total Patterns | N | N | +N |
| Total Success Traces | N | N | +N |
| Total Experiments | N | N | +N |

## What This Article Does NOT Cover
- <scope boundary>

## Open Questions / Unverified Claims
- <confidence changes marked as inference>

## Related
- [[wiki/apks/A-XXXXXX]] — triggering analysis
- [[wiki/techniques/T-XXXX]] — new/updated techniques
- [[wiki/patterns/P-XXXX]] — new/updated patterns
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `diff_id` | Yes | Format: KD-XXXX (sequential) |
| `analysis_id` | Yes | Triggering analysis |
| `trigger` | Yes | analysis-complete / experiment-complete / technique-updated / manual |
| `timestamp` | Yes | ISO 8601 |

### Content Rules
- **Generated automatically after each analysis** — never manual
- **Every change categorized** — NEW, UPDATED, CONFIDENCE, FAILURES, RELATIONSHIPS
- **Confidence deltas must have reasons** — reproduced, failed, refined
- **Metrics show KB growth** — quantitative learning tracking
- **Links to all affected entries** — full traceability