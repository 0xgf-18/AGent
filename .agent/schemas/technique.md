# Schema: Unpacking/Analysis Technique

> **Use when:** A reusable technique has been extracted from successful experiments.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)
> **Promotion states:** OBSERVED → CANDIDATE → VALIDATED → TRUSTED

---

## Template

```markdown
---
type: technique
topic: wiki/techniques/_index
source: <analysis_id or experiment_id>
tags: [tag1, tag2]
complexity: intermediate | advanced
completeness: stub | partial | complete
last_verified: YYYY-MM-DD
tool_versions: [<required tool versions>]
technique_id: <T-XXXX>
name: <Descriptive Technique Name>
category: unpacking | deobfuscation | anti-debug-bypass | anti-root-bypass | cert-pinning-bypass | dynamic-dump | static-analysis | other
problem: <What problem this technique solves>
applicable_indicators: [indicator1, indicator2]
prerequisites:
  tools: [tool_id1, tool_id2]
  environment: [requirement1, requirement2]
  host_tools: [tool_id1]
  device_tools: [tool_id2]
  root_required: true/false
  emulator_required: true/false
  architecture: [arm64-v8a, armeabi-v7a, x86, x86_64]
  android_version_min: <21>
  android_version_max: <34>
workflow: <reference to workflow steps below>
decision_points: [dp1, dp2]
success_indicators: [indicator1, indicator2]
verification_method: <how to verify success>
known_limitations: [limitation1, limitation2]
evidence: [analysis_id1, analysis_id2]
successful_analyses: [A-XXXXXX, A-YYYYYY]
failed_analyses: [A-ZZZZZZ]
confidence: 0.0-1.0
promotion_state: OBSERVED | CANDIDATE | VALIDATED | TRUSTED
version: <1>
previous_version: <T-XXXX vN>
version_reason: <why version changed>
created_timestamp: YYYY-MM-DDTHH:MM:SS
updated_timestamp: YYYY-MM-DDTHH:MM:SS
llm_summary: "<A dense, 1-2 sentence summary of the technique, its prerequisites, and when to apply it for direct LLM retrieval>"
---

# Technique T-XXXX: <Descriptive Technique Name>

## This Article Answers
- "How do I unpack/analyze <protection type>?"
- "When does technique T-XXXX apply?"
- "What are the prerequisites for T-XXXX?"

## Key Takeaways
- [PROBLEM] <what this technique solves>
- [PREREQUISITES] <tools, environment, conditions required>
- [WORKFLOW] <core steps in one line each>
- [VERIFICATION] <how to confirm it worked>
- [CONFIDENCE] <current confidence level>

## Problem Statement
- Protection class addressed: `<e.g., DexProtector 5.x, Bangcle, custom packer>`
- Why standard approaches fail: `<details>`
- Applicable when: `<indicators that suggest this technique>`

## Applicable Indicators
| Indicator | Type | Detection Method | Weight |
|---|---|---|---|
| `<indicator>` | static/dynamic | `<tool/check>` | High/Med/Low |

## Prerequisites
### Required Tools
| Tool ID | Name | Version | Host/Device | Purpose |
|---|---|---|---|---|
| `<tool_id>` | `<name>` | `<version>` | host/device | `<purpose>` |

### Required Environment
| Requirement | Details |
|---|---|
| Root | true/false |
| Emulator | true/false (specify: MuMu, Genymotion, etc.) |
| Architecture | `<ABI>` |
| Android Version | `<min>-<max>` |
| Writable Paths | `<paths>` |

## Workflow
### Step 1: <Step Name>
**Observation:** `<what you observe before this step>`
**Action:** `<exact command or operation>`
**Tool:** `<tool_id>`
**Expected Result:** `<what should happen>`
**Success Indicator:** `<how to know it worked>`
**Failure Mode:** `<what failure looks like>`

### Step 2: <Step Name>
...

### Step N: <Step Name>
...

## Decision Points
| Decision Point | Condition | If True | If False |
|---|---|---|---|
| DP1 | `<condition>` | `<action>` | `<action>` |

## Intermediate Observations
| Step | Observation | Significance |
|---|---|---|
| 1 | `<observation>` | `<why it matters>` |

## Success Indicators
- `<indicator 1>` — `<how to verify>`
- `<indicator 2>` — `<how to verify>`

## Verification Method
### Structural
- `<check>` — `<expected result>`

### Content
- `<check>` — `<expected result>`

### Parser
- `<check>` — `<expected result>`

### Downstream Analysis
- `<check>` — `<expected result>`

### Reproducibility
- `<check>` — `<expected result>`

**Final Status:** COMMAND_SUCCESS vs VERIFIED_SUCCESS (only VERIFIED_SUCCESS counts for learning)

## Known Failure Conditions
| Condition | Symptom | Workaround |
|---|---|---|
| `<condition>` | `<symptom>` | `<workaround or N/A>` |

## Limitations
- `<limitation 1>`
- `<limitation 2>`

## Evidence
| Analysis ID | APK SHA256 | Result | Notes |
|---|---|---|---|
| A-XXXXXX | `<hash>` | SUCCESS/FAIL | `<details>` |

## Successful Analyses
- A-XXXXXX — `<brief context>`
- A-YYYYYY — `<brief context>`

## Failed Analyses
- A-ZZZZZZ — `<why it failed>`

## Confidence Assessment
| Factor | Score (0-1) | Notes |
|---|---|---|
| Reproducibility | `<score>` | `<notes>` |
| Evidence Quality | `<score>` | `<notes>` |
| Independent Validation | `<score>` | `<notes>` |
| Environmental Stability | `<score>` | `<notes>` |
| **Overall** | `<score>` | |

## Promotion History
| State | Date | Evidence |
|---|---|---|
| OBSERVED | YYYY-MM-DD | `<initial observation>` |
| CANDIDATE | YYYY-MM-DD | `<first successful experiment>` |
| VALIDATED | YYYY-MM-DD | `<reproduced on 2nd APK>` |
| TRUSTED | YYYY-MM-DD | `<reproduced on 3+ independent APKs>` |

## Version History
| Version | Date | Change | Reason |
|---|---|---|---|
| 1 | YYYY-MM-DD | Initial | `<reason>` |

## What This Article Does NOT Cover
- <scope boundary>

## Open Questions / Unverified Claims
- <unverified assumption>

## Related
- [[wiki/patterns/P-XXXX]] — pattern this technique addresses
- [[wiki/experiments/EXP-XXXX]] — source experiment
- [[wiki/apks/A-XXXXXX]] — source analysis
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `technique_id` | Yes | Format: T-XXXX (sequential) |
| `name` | Yes | Descriptive, unique name |
| `category` | Yes | One of: unpacking, deobfuscation, anti-debug-bypass, anti-root-bypass, cert-pinning-bypass, dynamic-dump, static-analysis, other |
| `problem` | Yes | Clear problem statement |
| `applicable_indicators` | Yes | YAML array of detectable indicators |
| `prerequisites` | Yes | Structured tool/environment requirements |
| `workflow` | Yes | Step-by-step with observations |
| `verification_method` | Yes | Multi-category verification |
| `confidence` | Yes | Float 0.0-1.0 |
| `promotion_state` | Yes | OBSERVED / CANDIDATE / VALIDATED / TRUSTED |
| `version` | Yes | Integer version number |
| `evidence` | Yes | YAML array of analysis IDs |
| `successful_analyses` | Yes | YAML array |
| `failed_analyses` | Yes | YAML array |

### Content Rules
- **Every step must have Observation → Action → Tool → Expected Result → Success Indicator**
- **Verification must be multi-category** — structural, content, parser, downstream, reproducibility
- **Confidence must be justified** — break down by factors
- **Failed analyses are mandatory** — document where technique doesn't work
- **Version history is immutable** — never overwrite, only append
- **Promotion requires evidence** — CANDIDATE needs 1 success, VALIDATED needs 2+, TRUSTED needs 3+ independent