# Schema: Tool Registry Entry

> **Use when:** Registering a tool available for APK analysis.
> **Common metadata:** See [_common-metadata.md](_common-metadata.md)
> **Auto-discovered and manually curated** — single source of truth for tool capabilities.

---

## Template

```markdown
---
type: tool-registry
topic: wiki/tool-registry/_index
source: <auto-detection | manual>
tags: [tag1, tag2]
complexity: beginner
completeness: complete
last_verified: YYYY-MM-DD
tool_versions: []
tool_id: <TR-XXXX>
name: <Tool Name>
version: <version string>
path: <absolute path or package name>
category: apk-inspection | dex-analysis | resource-analysis | native-analysis | archive-analysis | static-analysis | dynamic-observation | filesystem-inspection | process-inspection | logging | comparison | report-generation | other
subcategory: <more specific category>
host_device: host | device | both
input_types: [apk, dex, so, odex, oat, jar, class, smali, binary, directory, process, log]
output_types: [dex, decompiled-java, smali, c-header, json, xml, text, binary, log, report]
capabilities: [capability1, capability2]
configuration: <config details or "default">
timeout_seconds: <default timeout>
verification_methods: [method1, method2]
availability: available | missing | deprecated | broken
install_method: <pip, apt, brew, download, build, adb-push, play-store>
install_command: <command to install>
install_notes: <notes>
dependencies: [tool_id1, tool_id2]
known_issues: [issue1, issue2]
works_on_architectures: [arm64-v8a, armeabi-v7a, x86, x86_64]
works_on_android: [<min-api>, <max-api>]
llm_summary: "<A dense, 1-2 sentence summary of the tool's purpose, key capabilities, and when to use it for direct LLM retrieval>"
---

# Tool: <TR-XXXX> — <Tool Name>

## This Article Answers
- "What does <tool> do?"
- "When should I use <tool>?"
- "How do I install/verify <tool>?"
- "What are <tool>'s limitations?"

## Key Takeaways
- [PURPOSE] <one-line purpose>
- [CATEGORY] <primary category>
- [INPUTS] <accepted input types>
- [OUTPUTS] <produced output types>
- [AVAILABILITY] available/missing/deprecated

## Basic Information
| Property | Value |
|---|---|
| Tool ID | TR-XXXX |
| Name | `<name>` |
| Version | `<version>` |
| Path | `<path>` |
| Category | `<category>` |
| Subcategory | `<subcategory>` |
| Host/Device | host / device / both |
| Availability | available / missing / deprecated / broken |

## Capabilities
| Capability | Description | Verified |
|---|---|---|
| `<capability>` | `<description>` | Yes/No |

## Input/Output Types
| Direction | Type | Format | Notes |
|---|---|---|---|
| Input | `<type>` | `<format>` | `<notes>` |
| Output | `<type>` | `<format>` | `<notes>` |

## Installation
**Method:** `<pip | apt | brew | download | build | adb-push | play-store>`
**Command:** `<verbatim install command>`
**Notes:** `<additional notes, version pinning, etc.>`

**Verification Command:** `<command to verify installation>`
**Expected Output:** `<expected version/output>`

## Configuration
**Default Config:** `<config details>`
**Common Flags:** `<flags>`
**Environment Variables:** `<vars>`

## Usage Examples
### Example 1: <Purpose>
```bash
<command>
```
**Input:** `<file/type>`
**Output:** `<file/type>`
**When to Use:** `<scenario>`

### Example 2: <Purpose>
...

## Compatibility
| Architecture | Supported | Tested |
|---|---|---|
| arm64-v8a | Yes/No | Yes/No |
| armeabi-v7a | Yes/No | Yes/No |
| x86 | Yes/No | Yes/No |
| x86_64 | Yes/No | Yes/No |

| Android API | Supported | Tested |
|---|---|---|
| 21-23 | Yes/No | Yes/No |
| 24-28 | Yes/No | Yes/No |
| 29-30 | Yes/No | Yes/No |
| 31-33 | Yes/No | Yes/No |
| 34+ | Yes/No | Yes/No |

## Known Issues
| Issue | Severity | Workaround | Status |
|---|---|---|---|
| `<issue>` | High/Med/Low | `<workaround>` | Open/Fixed |

## Dependencies
| Tool ID | Name | Required | Version Constraint |
|---|---|---|---|
| TR-XXXX | `<name>` | Yes/No | `<constraint>` |

## Performance
| Metric | Value | Conditions |
|---|---|---|
| Typical Runtime | `<seconds>` | `<conditions>` |
| Memory Usage | `<MB>` | `<conditions>` |
| Output Size | `<MB>` | `<conditions>` |

## Verification Methods
| Method | Description | Command |
|---|---|---|
| `<method>` | `<description>` | `<command>` |

## What This Article Does NOT Cover
- <scope boundary>

## Open Questions / Unverified Claims
- <unverified capability>

## Related
- [[wiki/techniques/T-XXXX]] — techniques requiring this tool
- Runtime availability — run `tool_discover.py` (never stored)
```

---

## Key Rules for This Schema

### Schema-Specific Fields
| Field | Required | Notes |
|---|---|---|
| `tool_id` | Yes | Format: TR-XXXX (sequential) |
| `name` | Yes | Tool name |
| `version` | Yes | Version string (empty if not installed) |
| `path` | Yes | Absolute path or package name |
| `category` | Yes | One of the defined categories |
| `host_device` | Yes | host / device / both |
| `input_types` | Yes | YAML array |
| `output_types` | Yes | YAML array |
| `capabilities` | Yes | YAML array |
| `availability` | Yes | available / missing / deprecated / broken |
| `install_method` | Conditional | Required if availability != available |
| `install_command` | Conditional | Required if availability != available |

### Content Rules
- **Auto-discovery populates initial registry** — manual curation refines
- **Availability is explicit** — missing tools have install instructions
- **Capabilities are specific** — not generic descriptions
- **Compatibility matrix is mandatory** — architecture + Android version
- **Verification methods enable health checks** — how to confirm tool works
- **Dependencies link to other registry entries** — not external references