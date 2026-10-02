# Schema: APK Analysis

> **Use when:** Source is an APK file being analyzed for reverse engineering.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)

---

## Template

```markdown
---
type: apk-analysis
topic: wiki/apk/_index
source: <APK file path or SHA256>
tags: [tag1, tag2]
complexity: intermediate | advanced
completeness: stub | partial | complete
last_verified: YYYY-MM-DD
tool_versions: [<if applicable>]
apk_sha256: <SHA256 of the APK>
package_name: <com.example.app>
version_name: <1.0.0>
version_code: <1>
min_sdk: <21>
target_sdk: <34>
architectures: [arm64-v8a, armeabi-v7a, x86, x86_64]
protection_detected: [packer-name, obfuscator-name, anti-tamper, anti-debug]
analysis_id: <A-XXXXXX>
status: in-progress | complete | abandoned
bypass_status: complete | partial | failed | not-attempted
llm_summary: "<A dense, 1-2 sentence summary of the APK's protection mechanisms and analysis findings for direct LLM retrieval>"
---

# <Package Name> — APK Analysis

## This Article Answers
- "What protections does <package> use?"
- "How can <package> be unpacked/analyzed?"
- "What techniques were successful against <protection>?"

## Key Takeaways
- [PROTECTION] <primary protection mechanism identified>
- [PACKER] <packer name and version if detected>
- [OBSERVATION] <key structural or behavioral observation>
- [RESULT] <final analysis outcome>

## APK Fingerprint
| Property | Value |
|---|---|
| SHA256 | `<hash>` |
| Package | `com.example.app` |
| Version | `1.0.0` (code: 1) |
| Min SDK | 21 |
| Target SDK | 34 |
| Architectures | `arm64-v8a, armeabi-v7a` |
| File Size | `XX MB` |
| DEX Count | `N` |
| Native Libraries | `N` |

## Protection Detection Results
| Protection Type | Detected | Tool | Confidence | Details |
|---|---|---|---|---|
| Packer | Yes/No | <tool> | High/Med/Low | <details> |
| Obfuscator | Yes/No | <tool> | High/Med/Low | <details> |
| Anti-Debug | Yes/No | <tool> | High/Med/Low | <details> |
| Anti-Tamper | Yes/No | <tool> | High/Med/Low | <details> |
| Anti-Root | Yes/No | <tool> | High/Med/Low | <details> |
| Certificate Pinning | Yes/No | <tool> | High/Med/Low | <details> |
| Custom Protection | Yes/No | <tool> | High/Med/Low | <details> |

## Static Analysis Findings
### DEX Analysis
- Entry point: `<class.method>`
- Obfuscation indicators: `<details>`
- String encryption: `<details>`
- Class count: `<N>`

### Native Library Analysis
| Library | Architecture | Exports | Suspicious Functions | Protection Signs |
|---|---|---|---|---|
| `libnative.so` | arm64-v8a | `JNI_OnLoad, ...` | `decrypt, check` | `packed` |

### Resource Analysis
- Assets: `<list>`
- Raw resources: `<list>`
- Suspicious files: `<details>`

## Dynamic Analysis Observations
### Runtime Behavior (MuMu)
- Process name: `<name>`
- Native library load order: `<list>`
- Anti-debug triggers: `<details>`
- Network behavior: `<details>`
- File system access: `<details>`

### Frida/Objection Hooks Attempted
| Hook Target | Result | Notes |
|---|---|---|
| `java.lang.ClassLoader.loadClass` | Success/Failed | `<details>` |
| `dlopen` | Success/Failed | `<details>` |

## Experiments Conducted
| Experiment ID | Technique | Tools | Environment | Result | Verification |
|---|---|---|---|---|---|
| EXP-001 | <technique> | <tools> | <env> | SUCCESS/FAIL | VERIFIED/UNVERIFIED |

## Successful Workflow (if any)
> References: [[wiki/techniques/T-XXXX]] | [[wiki/experiments/EXP-XXXX]]

## Failed Attempts
| Attempt | Technique | Failure Reason | Evidence |
|---|---|---|---|
| 1 | <technique> | <reason> | <details> |

## Extracted Artifacts
| Artifact ID | Type | Source Experiment | Hash | Location | Verified |
|---|---|---|---|---|---|
| ART-XXXX | DEX/DEXES/SO/OTHER | EXP-XXXX | `<hash>` | `<path>` | Yes/No |

## What This Article Does NOT Cover
- <scope boundary>

## Open Questions / Unverified Claims
- <unconfirmed observation>
- <conflicting data>

## Related
- [[wiki/techniques/T-XXXX]] — technique used
- [[wiki/experiments/EXP-XXXX]] — experiment record
- [[wiki/patterns/P-XXXX]] — matched pattern
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `apk_sha256` | Yes | SHA256 of the analyzed APK |
| `package_name` | Yes | Application package name |
| `version_name` | Yes | Version name from manifest |
| `version_code` | Yes | Version code from manifest |
| `min_sdk` | Yes | Minimum SDK version |
| `target_sdk` | Yes | Target SDK version |
| `architectures` | Yes | YAML array of supported ABIs |
| `protection_detected` | Yes | YAML array of detected protections |
| `analysis_id` | Yes | Unique analysis identifier (A-XXXXXX) |
| `status` | Yes | `in-progress` / `complete` / `abandoned` |
| `bypass_status` | Yes | `complete` / `partial` / `failed` / `not-attempted` |

### Content Rules
- **Fingerprint table is mandatory** — exact hashes, versions, architecture
- **Protection detection must cite tools** — every detection claim needs tool + confidence
- **Experiments table links to experiment records** — never inline full experiment details
- **Artifacts tracked by hash** — large binaries referenced, not embedded
- **Failed attempts are as valuable as successes** — document what didn't work and why