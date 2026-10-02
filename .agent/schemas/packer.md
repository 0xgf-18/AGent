# Schema — Packer

> **Use when:** an unpacking experiment beats a protection (or adds a variant).
> **Primary reuse artifact:** packer name -> verified unpacking method, so a
> fresh agent can unpack the same (or a similar) APK without redoing the RE.
> **Write with:** `python .kb/scripts/record_packer.py --payload p.json`
> (validates everything below; refuses unverified `unpacked` claims).

---

## Frontmatter

```yaml
---
type: packer
topic: wiki/packers/_index
source: <documented_in or first evidence id>
tags: [packer, ...]
complexity: advanced
completeness: complete
last_verified: YYYY-MM-DD
packer_id: <slug>                 # stable, names the file (a-z, 0-9, -)
name: "<packer display name>"
aliases: ["..."]                  # vendor names, class/lib markers
protection_class: packer
first_seen: YYYY-MM-DD
indicators: ["..."]               # non-empty: how to recognize it
unpacking_status: not_attempted | attempted | unpacked | blocked
confidence: 0.0-1.0
evidence: [EXP-XXXX]              # experiment ids (must exist)
technique_ids: [T-XXXX]
tools: [TR-XXXX]
documented_in: "<playbook/wiki source>"
version: 1
previous_version: ""
version_reason: "initial recording"
created_timestamp: ISO8601
updated_timestamp: ISO8601
llm_summary: "<dense 1-2 sentence summary>"
---
```

## Content rules (enforced by record_packer.py)

| Rule | Enforcement |
|---|---|
| `packer_id` slug names the file; new packer -> new article | create vs update path |
| `unpacking_status: unpacked` requires >=1 VERIFIED_SUCCESS experiment in `evidence` OR non-empty `documented_in` | exit 4 with problem list |
| every `evidence` id must exist as an experiment article | exit 4 |
| `unpacking_method` steps need `name` + `action` | exit 4 |
| `verification` non-empty (category / check / pass-condition rows) | exit 4 |
| updates bump `version` by exactly 1 + `version_reason` + `previous_version` (immutable history) | exit 4 |

## Required body sections

This Article Answers · Key Takeaways · Identification · Unpacking Status ·
Unpacking Method (stepwise, with Tool/Expected/Success Indicator/Failure Mode) ·
Decision Points · Verification · Known Failure Conditions · Evidence ·
Version History · What This Article Does NOT Cover · Related

## Related
- `.kb/scripts/record_packer.py` — write mechanism
- `wiki/packers/_index.md` — generated topic index
- `.kb/experiment-protocol.md` Phase 4 — when to store a packer
