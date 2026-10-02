# Schema: Success Trace

> **Use when:** A verified successful experiment produces a usable result.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)
> **Created only for VERIFIED_SUCCESS** — never for COMMAND_SUCCESS alone.

---

## Template

```markdown
---
type: success-trace
topic: wiki/success-traces/_index
source: <experiment_id>
tags: [tag1, tag2]
complexity: advanced
completeness: complete
last_verified: YYYY-MM-DD
tool_versions: [<tool versions used>]
success_trace_id: <ST-XXXX>
analysis_id: <A-XXXXXX>
experiment_id: <EXP-XXXX>
input_sha256: <APK SHA256>
environment_id: host-runtime  # device state probed live, never stored
techniques_used: [T-XXXX, T-YYYY]
tools_used: [tool_id1, tool_id2]
final_result: VERIFIED_SUCCESS
verification_categories: [STRUCTURAL, CONTENT, PARSER, DOWNSTREAM_ANALYSIS, REPRODUCIBILITY]
confidence: 0.0-1.0
causality_analysis: <INFERENCE | SUPPORTED>
llm_summary: "<A dense, 1-2 sentence summary of the successful workflow, key factors, and resulting technique for direct LLM retrieval>"
---

# Success Trace ST-XXXX

## This Article Answers
- "What exactly led to success in analysis A-XXXXXX?"
- "Which factors were essential vs incidental?"
- "Can this workflow be reproduced?"

## Key Takeaways
- [SUCCESS] <one-line summary of what was achieved>
- [ESSENTIAL_FACTORS] <what was necessary for success>
- [WORKFLOW] <condensed successful chain>
- [VERIFICATION] <how success was confirmed>
- [CONFIDENCE] <level and basis>

## Context
| Property | Value |
|---|---|
| Analysis ID | A-XXXXXX |
| Experiment ID | EXP-XXXX |
| Input APK SHA256 | `<hash>` |
| Environment | `<env-id>` (e.g., mumu-rooted-001) |
| Date | YYYY-MM-DD |

## Environment Profile (Snapshot at Time of Success)
> Environment: host-runtime (runtime-only; never stored)
- Device: MuMu
- ADB: available
- Root: available (via su)
- Architecture: x86_64
- Android Version: 15
- Host Tools: [list with versions]
- Device Tools: [list with versions]
- Available Storage: `<GB>`
- Writable Paths: [list]

## Experiment Sequence

### Step 1
**Observation:** `<what was observed before this step>`
**Action:** `<exact command, script, or operation performed>`
**Tool:** `<tool_id>` (version: `<version>`)
**Host/Device:** host | device
**Command:** `<verbatim command executed>`
**Duration:** `<seconds>`
**Result:** `<output, files created, state changes>`
**Success Indicator Observed:** `<specific indicator that this step worked>`
**Artifacts Produced:** [ART-XXXX, ART-YYYY]

### Step 2
...

### Step N
...

## Failed Attempts Before Success
> These attempts immediately preceded the successful workflow and provide critical context.

### Attempt 1 (EXP-XXXX-FAIL-1)
**Technique:** `<technique_id or description>`
**Tools:** [tool_ids]
**Action:** `<what was attempted>`
**Result:** FAILED
**Failure Reason:** `<root cause if known>`
**Observation:** `<what was learned>`
**Why It Matters:** `<how this informed the successful approach>`

### Attempt 2 (EXP-XXXX-FAIL-2)
...

## Final Result Verification
| Category | Check | Expected | Actual | Status |
|---|---|---|---|---|
| STRUCTURAL | `<check>` | `<expected>` | `<actual>` | PASS/FAIL |
| CONTENT | `<check>` | `<expected>` | `<actual>` | PASS/FAIL |
| PARSER | `<check>` | `<expected>` | `<actual>` | PASS/FAIL |
| DOWNSTREAM_ANALYSIS | `<check>` | `<expected>` | `<actual>` | PASS/FAIL |
| REPRODUCIBILITY | `<check>` | `<expected>` | `<actual>` | PASS/FAIL |

**Overall:** VERIFIED_SUCCESS

## Success Causality Analysis
> **Marked as INFERENCE until supported by additional experiments.**

### ESSENTIAL (necessary for success)
| Factor | Evidence | Confidence |
|---|---|---|
| `<factor>` | `<supporting observation>` | High/Med/Low |

### LIKELY_RELEVANT (contributed but not strictly necessary)
| Factor | Evidence | Confidence |
|---|---|---|

### OPTIONAL (helpful but not required)
| Factor | Evidence | Confidence |
|---|---|---|

### IRRELEVANT (did not affect outcome)
| Factor | Evidence | Confidence |
|---|---|---|

**Causality Status:** INFERENCE | SUPPORTED_BY_ADDITIONAL_EXPERIMENTS

## Extracted Technique
> **Reference:** [[wiki/techniques/T-XXXX]]
**Technique ID:** T-XXXX (created/updated from this trace)
**Generalized From:** This specific success trace
**Abstraction Level:** `<what was generalized vs kept specific>`

## Artifacts Produced
| Artifact ID | Type | Hash | Size | Location | Verified | Downstream Usable |
|---|---|---|---|---|---|---|
| ART-XXXX | DEX/DEXES/SO/OTHER | `<hash>` | `<bytes>` | `<path>` | Yes/No | Yes/No |

## Before/After Comparison
| Property | Input (APK) | Intermediate | Output (Final) |
|---|---|---|---|
| File Type | APK | `<type>` | `<type>` |
| SHA256 | `<hash>` | `<hash>` | `<hash>` |
| Parseable | Yes/No | Yes/No | Yes/No |
| DEX Count | N | N | N |
| Class Count | N | N | N |
| Method Count | N | N | N |
| Native Libs | N | N | N |

## Reproducibility Test
**Performed:** Yes/No
**Date:** YYYY-MM-DD
**Result:** SUCCESS/FAIL
**Notes:** `<details>`

## Knowledge Diff Generated
> References: [[wiki/knowledge-diffs/KD-XXXX]]
- NEW: Technique T-XXXX (or updated T-XXXX vN)
- CONFIDENCE CHANGES: T-XXXX: 0.XX → 0.YY
- NEW RELATIONSHIPS: Pattern P-XXXX → Technique T-XXXX

## What This Article Does NOT Cover
- <scope boundary>

## Open Questions / Unverified Claims
- <causality claims marked INFERENCE>
- <environment-specific behaviors>

## Related
- [[wiki/apks/A-XXXXXX]] — source analysis
- [[wiki/experiments/EXP-XXXX]] — source experiment
- [[wiki/techniques/T-XXXX]] — extracted/updated technique
- environment: host-runtime (runtime-only, never stored)
- [[wiki/knowledge-diffs/KD-XXXX]] — knowledge changes
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `success_trace_id` | Yes | Format: ST-XXXX (sequential) |
| `analysis_id` | Yes | Links to APK analysis |
| `experiment_id` | Yes | Links to experiment record |
| `input_sha256` | Yes | APK that was successfully analyzed |
| `environment_id` | Yes | `host-runtime` (device state never stored) |
| `techniques_used` | Yes | YAML array of technique IDs |
| `tools_used` | Yes | YAML array of tool IDs |
| `final_result` | Yes | Must be `VERIFIED_SUCCESS` |
| `verification_categories` | Yes | YAML array of verification types passed |
| `confidence` | Yes | Float 0.0-1.0 |
| `causality_analysis` | Yes | `INFERENCE` or `SUPPORTED` |

### Content Rules
- **Every step must be verbatim** — exact commands, outputs, observations
- **Failed attempts before success are mandatory** — they provide critical context
- **Causality analysis is explicitly marked INFERENCE** — never treated as fact without additional experiments
- **Verification must be multi-category** — at least 3 of 5 categories for VERIFIED_SUCCESS
- **Before/After comparison is mandatory** — proves genuine transformation
- **Reproducibility test should be attempted** — documents if result is repeatable
- **Links to extracted technique** — trace → technique relationship explicit