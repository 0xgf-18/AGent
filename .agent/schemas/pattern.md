# Schema: Protection Pattern

> **Use when:** A recurring protection mechanism pattern is identified across multiple APKs.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)
> **Links analyses to techniques** — enables pattern-based technique retrieval.

---

## Template

```markdown
---
type: pattern
topic: wiki/patterns/_index
source: <analysis_id or research>
tags: [tag1, tag2]
complexity: intermediate
completeness: partial | complete
last_verified: YYYY-MM-DD
tool_versions: []
pattern_id: <P-XXXX>
name: <Descriptive Pattern Name>
category: packer | obfuscator | anti-debug | anti-tamper | anti-root | cert-pinning | integrity-check | custom | other
protection_type: <specific protection family>
indicators:
  static: [indicator1, indicator2]
  dynamic: [indicator1, indicator2]
  structural: [indicator1, indicator2]
applicable_techniques: [T-XXXX, T-YYYY]
confidence: 0.0-1.0
first_seen: YYYY-MM-DD
last_seen: YYYY-MM-DD
analyses_matched: [A-XXXXXX, A-YYYYYY]
llm_summary: "<A dense, 1-2 sentence summary of the pattern, its indicators, and associated techniques for direct LLM retrieval>"
---

# Pattern P-XXXX: <Descriptive Pattern Name>

## This Article Answers
- "What is the <protection> pattern?"
- "How do I detect <protection>?"
- "What techniques work against <protection>?"

## Key Takeaways
- [PATTERN] <protection family and variant>
- [INDICATORS] <key static/dynamic/structural indicators>
- [TECHNIQUES] <associated technique IDs>
- [CONFIDENCE] <detection confidence>

## Pattern Description
**Protection Family:** `<e.g., DexProtector, Bangcle, Kiwi, custom>`
**Variant/Version:** `<if known>`
**Type:** `<packer/obfuscator/anti-debug/etc.>`
**Target:** `<what it protects: DEX, native, resources, etc.>`

## Detection Indicators

### Static Indicators
| Indicator | Location | Detection Method | Weight | Example |
|---|---|---|---|---|
| `<indicator>` | `<file/offset/class>` | `<tool/check>` | High/Med/Low | `<example>` |

### Dynamic Indicators
| Indicator | Trigger | Detection Method | Weight | Example |
|---|---|---|---|---|
| `<indicator>` | `<condition>` | `<tool/check>` | High/Med/Low | `<example>` |

### Structural Indicators
| Indicator | Description | Weight |
|---|---|---|
| `<indicator>` | `<description>` | High/Med/Low |

## Detection Logic
```python
# Pseudocode for pattern detection
def detect_pattern(apk_analysis):
    score = 0
    if <static_indicator_1>:
        score += <weight>
    if <static_indicator_2>:
        score += <weight>
    # ...
    return score > <threshold>
```

## Associated Techniques
| Technique ID | Name | Applicability | Confidence | Notes |
|---|---|---|---|---|
| T-XXXX | `<name>` | High/Med/Low | 0.0-1.0 | `<notes>` |

## Known Variants
| Variant | Differences | Detection Adjustments |
|---|---|---|
| `<variant>` | `<differences>` | `<adjustments>` |

## Matched Analyses
| Analysis ID | APK SHA256 | Match Confidence | Notes |
|---|---|---|---|
| A-XXXXXX | `<hash>` | 0.0-1.0 | `<details>` |

## False Positives
| APK SHA256 | Reason | Resolution |
|---|---|---|
| `<hash>` | `<reason>` | `<resolution>` |

## False Negatives
| APK SHA256 | Reason | Resolution |
|---|---|---|
| `<hash>` | `<reason>` | `<resolution>` |

## Evolution History
| Date | Change | Evidence |
|---|---|---|
| YYYY-MM-DD | `<change>` | `<analysis_id>` |

## What This Article Does NOT Cover
- <scope boundary>

## Open Questions / Unverified Claims
- <unverified variant>

## Related
- [[wiki/techniques/T-XXXX]] — techniques for this pattern
- [[wiki/apks/A-XXXXXX]] — analyses matching this pattern
- [[wiki/ttp-index]] — MITRE ATT&CK mapping if applicable
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `pattern_id` | Yes | Format: P-XXXX (sequential) |
| `name` | Yes | Descriptive name |
| `category` | Yes | packer/obfuscator/anti-debug/anti-tamper/anti-root/cert-pinning/integrity-check/custom/other |
| `protection_type` | Yes | Specific family name |
| `indicators` | Yes | Structured static/dynamic/structural |
| `applicable_techniques` | Yes | YAML array of technique IDs |
| `confidence` | Yes | Float 0.0-1.0 |
| `first_seen` | Yes | Date first observed |
| `last_seen` | Yes | Date last observed |
| `analyses_matched` | Yes | YAML array of analysis IDs |

### Content Rules
- **Indicators must be specific and detectable** — not vague descriptions
- **Detection logic should be implementable** — pseudocode or clear rules
- **False positives/negatives tracked** — improves pattern over time
- **Evolution history** — patterns change, track versions
- **Links to techniques** — enables planner to retrieve applicable techniques