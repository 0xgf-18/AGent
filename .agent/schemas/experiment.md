# Schema: Experiment Record

> **Use when:** Any experiment is conducted during APK analysis.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)
> **Created for EVERY experiment** — success, partial, or failure.

---

## Template

```markdown
---
type: experiment
topic: wiki/experiments/_index
source: <analysis_id>
tags: [tag1, tag2]
complexity: intermediate | advanced
completeness: complete
last_verified: YYYY-MM-DD
tool_versions: [<tool versions used>]
experiment_id: <EXP-XXXX>
analysis_id: <A-XXXXXX>
technique_id: <T-XXXX or "exploratory">
toolset: [tool_id1, tool_id2]
environment_id: host-runtime  # device state probed live, never stored
input_fingerprint: <APK SHA256 + relevant characteristics>
timestamp: YYYY-MM-DDTHH:MM:SS
steps: <count>
result: SUCCESS | PARTIAL | FAILURE
verification_status: UNVERIFIED | COMMAND_SUCCESS | VERIFIED_SUCCESS
failure_category: TECHNIQUE | TOOL | ENVIRONMENT | APK | VERIFICATION | UNKNOWN
notes: "<brief summary>"
llm_summary: "<A dense, 1-2 sentence summary of the experiment, approach, and outcome for direct LLM retrieval>"
---

# Experiment EXP-XXXX

## This Article Answers
- "What was attempted in this experiment?"
- "What was the result?"
- "What was learned (success or failure)?"

## Key Takeaways
- [APPROACH] <technique or exploratory approach>
- [TOOLS] <tools used>
- [RESULT] SUCCESS/PARTIAL/FAILURE
- [LEARNING] <key insight>

## Context
| Property | Value |
|---|---|
| Experiment ID | EXP-XXXX |
| Analysis ID | A-XXXXXX |
| Technique | T-XXXX or "exploratory" |
| Environment | `<env-id>` |
| Timestamp | YYYY-MM-DDTHH:MM:SS |
| Input APK | `<SHA256>` |

## Prerequisites Check
| Requirement | Required | Available | Met |
|---|---|---|---|
| `<tool>` | Yes/No | Yes/No | Yes/No |
| Root | Yes/No | Yes/No | Yes/No |
| Emulator | Yes/No | Yes/No | Yes/No |
| Architecture | `<abi>` | `<abi>` | Yes/No |
| Android Version | `<min-max>` | `<version>` | Yes/No |

**Prerequisites Met:** ALL / PARTIAL / NONE

## Steps
### Step 1
**Observation:** `<what prompted this step>`
**Action:** `<exact operation>`
**Tool:** `<tool_id>` (version: `<version>`)
**Host/Device:** host | device
**Command/Script:** `<verbatim>`
**Input:** `<files, state>`
**Expected:** `<expected outcome>`
**Actual Result:** `<what happened>`
**Duration:** `<seconds>`
**Output Artifacts:** [ART-XXXX]
**Success Indicators Observed:** [indicator1, indicator2]

### Step 2
...

### Step N
...

## Observations
| Step | Observation | Significance |
|---|---|---|
| 1 | `<observation>` | `<why it matters>` |

## Artifacts Produced
| Artifact ID | Type | Hash | Size | Location | Verified |
|---|---|---|---|---|---|
| ART-XXXX | DEX/DEXES/SO/LOG/OTHER | `<hash>` | `<bytes>` | `<path>` | Yes/No |

## Result
**Status:** SUCCESS | PARTIAL | FAILURE
**Verification:** UNVERIFIED | COMMAND_SUCCESS | VERIFIED_SUCCESS
**Failure Category (if failed):** TECHNIQUE | TOOL | ENVIRONMENT | APK | VERIFICATION | UNKNOWN

### If SUCCESS/PARTIAL:
**Success Indicators Met:** [indicator1, indicator2]
**Verification Performed:** [categories]
**Downstream Usable:** Yes/No

### If FAILURE:
**Failure Point:** Step `<N>`
**Failure Symptom:** `<what went wrong>`
**Root Cause Hypothesis:** `<why it failed>`
**Evidence:** `<logs, errors, state>`
**Recovery Action:** `<what was tried next>`

## Before/After Comparison
| Property | Before | After |
|---|---|---|
| File/State | `<description>` | `<description>` |
| SHA256 | `<hash>` | `<hash>` |
| Parseable | Yes/No | Yes/No |
| Key Metric | `<value>` | `<value>` |

## Failure Information (if applicable)
**Failure Category:** TECHNIQUE | TOOL | ENVIRONMENT | APK | VERIFICATION | UNKNOWN
**Detailed Reason:** `<explanation>`
**Known Issue:** Yes/No (references [[wiki/known-issues/...]])
**Workaround Attempted:** `<description>`
**Next Technique to Try:** T-XXXX or "exploratory"

## Learning Extracted
- **What worked:** `<specific steps/conditions>`
- **What didn't work:** `<specific steps/conditions>`
- **Environment sensitivity:** `<observations>`
- **Tool version sensitivity:** `<observations>`
- **New indicators discovered:** [indicator1, indicator2]
- **Refined applicability for technique:** `<how this refines T-XXXX>`

## Related
- [[wiki/apks/A-XXXXXX]] — parent analysis
- [[wiki/techniques/T-XXXX]] — technique tested (if any)
- environment: host-runtime (probed live via env_probe.py --health; never stored)
- [[wiki/success-traces/ST-XXXX]] — if this became a success trace
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `experiment_id` | Yes | Format: EXP-XXXX (sequential) |
| `analysis_id` | Yes | Parent analysis |
| `technique_id` | Yes | Technique tested, or "exploratory" |
| `toolset` | Yes | YAML array of tool IDs |
| `environment_id` | Yes | `host-runtime` (device state never stored) |
| `input_fingerprint` | Yes | APK SHA256 + key characteristics |
| `result` | Yes | SUCCESS / PARTIAL / FAILURE |
| `verification_status` | Yes | UNVERIFIED / COMMAND_SUCCESS / VERIFIED_SUCCESS |
| `failure_category` | Conditional | Required if FAILURE |

### Content Rules
- **Every experiment gets a record** — no exceptions
- **Verbatim commands and outputs** — no summarization
- **Failure category is mandatory for failures** — enables root-cause analysis
- **Learning extracted is mandatory** — even failed experiments produce knowledge
- **Prerequisites check is mandatory** — distinguishes environment vs technique failures
- **Before/After comparison** — proves whether transformation occurred