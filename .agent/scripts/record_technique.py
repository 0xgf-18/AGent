#!/usr/bin/env python3
"""
Extract or update a technique article — Phase 4 of the research loop
(see .kb/schemas/technique.md).

Rules enforced:
  - promotion evidence: CANDIDATE >=1 VERIFIED experiment in evidence,
    VALIDATED >=2 independent analyses, TRUSTED >=3 (refuses promotions
    without evidence - promotion requires evidence, schema Content Rules)
  - evidence experiment ids must exist and be VERIFIED_SUCCESS
  - every workflow step needs observation/action/tool/expected/success_indicator
  - new technique -> allocate next T-XXXX (v1); update -> version must be
    previous+1, version_reason required, existing Version History appended
    (immutable history - never rewrite old rows)

Usage:
    python record_technique.py --payload t.json [--dry-run]

Exit: 0 written, 4 validation failed, 5 io error.
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_ids  # noqa: E402

WIKI = Path(__file__).resolve().parent.parent.parent / "vault" / "articles"
TECHS = WIKI / "techniques"

CATEGORIES = ("unpacking", "deobfuscation", "anti-debug-bypass", "anti-root-bypass",
              "cert-pinning-bypass", "dynamic-dump", "static-analysis", "other")
STATES = ("OBSERVED", "CANDIDATE", "VALIDATED", "TRUSTED")
STEP_KEYS = ("observation", "action", "tool", "expected", "success_indicator")


def load_fm(rel: str) -> dict | None:
    path = WIKI / f"{rel}.md"
    if not path.exists():
        return None
    try:
        import yaml
        text = path.read_text(encoding="utf-8", errors="ignore")
        return yaml.safe_load(text.split("---", 2)[1]) or {}
    except Exception:
        return None


def check_evidence(exp_ids: list) -> tuple[list, list]:
    """Return (verified_analysis_ids, problems)."""
    verified, problems = [], []
    for eid in exp_ids or []:
        fm = load_fm(f"experiments/{eid}")
        if fm is None:
            problems.append(f"evidence {eid}: experiment article not found")
            continue
        if fm.get("verification_status") == "VERIFIED_SUCCESS":
            aid = fm.get("analysis_id")
            if aid and aid not in verified:
                verified.append(aid)
        else:
            problems.append(f"evidence {eid}: verification_status="
                            f"{fm.get('verification_status')!r} (not VERIFIED_SUCCESS)")
    return verified, problems


def validate(p: dict, existing: dict | None) -> list[str]:
    errs = []
    for req in ("name", "category", "problem", "applicable_indicators", "prerequisites",
                "workflow", "success_indicators", "verification_method",
                "known_limitations", "evidence", "successful_analyses",
                "confidence", "promotion_state", "llm_summary", "tags"):
        if p.get(req) in (None, "", []):
            errs.append(f"missing required field: {req}")
    for req in ("failed_analyses", "decision_points"):  # required present, may be empty
        if p.get(req) is None:
            errs.append(f"missing required field: {req}")
    if p.get("category") not in CATEGORIES:
        errs.append(f"category must be one of {CATEGORIES}")
    state = p.get("promotion_state")
    if state not in STATES:
        errs.append(f"promotion_state must be one of {STATES}")
    try:
        conf = float(p.get("confidence", -1))
        if not 0.0 <= conf <= 1.0:
            errs.append("confidence must be 0.0-1.0")
    except (TypeError, ValueError):
        errs.append("confidence must be numeric 0.0-1.0")

    for i, s in enumerate(p.get("workflow") or [], 1):
        missing = [k for k in STEP_KEYS if not s.get(k)]
        if missing:
            errs.append(f"workflow step {i} missing {missing} "
                        "(Observation->Action->Tool->Expected->Success Indicator)")

    # evidence cross-check + promotion rules
    verified, problems = check_evidence(p.get("evidence"))
    errs.extend(problems)
    succ = p.get("successful_analyses") or []
    if state == "CANDIDATE" and not verified:
        errs.append("CANDIDATE requires >=1 VERIFIED_SUCCESS experiment in evidence")
    if state == "VALIDATED" and len(verified) < 2:
        errs.append(f"VALIDATED requires >=2 independent verified analyses (have {len(verified)})")
    if state == "TRUSTED" and len(verified) < 3:
        errs.append(f"TRUSTED requires >=3 independent verified analyses (have {len(verified)})")
    if succ and verified and not set(succ).issubset(set(verified)):
        errs.append(f"successful_analyses {sorted(set(succ) - set(verified))} "
                    "not backed by VERIFIED evidence")

    # versioning
    if existing:
        old_v = int(existing.get("version", 1))
        new_v = p.get("version")
        if new_v != old_v + 1:
            errs.append(f"version must be {old_v + 1} for an update (got {new_v})")
        if not p.get("version_reason"):
            errs.append("updates require version_reason (version history immutable)")
        if not p.get("previous_version"):
            errs.append(f"updates require previous_version: '{existing.get('technique_id')} v{old_v}'")
    else:
        if p.get("version", 1) != 1:
            errs.append("new technique must start at version 1")
    return errs


def render(p: dict, t_id: str, existing: dict | None, tech_md: str | None) -> str:
    now = p.get("created_timestamp") or dt.datetime.now().isoformat(timespec="seconds")
    prev = p.get("previous_version", "")
    # merge version history: keep existing rows (immutable), append new
    old_rows = ""
    if existing and tech_md:
        m = re.search(r"## Version History\n\|[^\n]*\n\|[-| ]+\|\n((?:\|[^\n]*\n)+)", tech_md)
        if m:
            old_rows = m.group(1).rstrip("\n") + "\n"
    new_row = f"| {p.get('version', 1)} | {now[:10]} | {p.get('change_summary', 'Update')} | {p.get('version_reason', 'initial extraction')} |"

    pre = p["prerequisites"]
    wf = []
    for i, s in enumerate(p["workflow"], 1):
        wf.append(f"""### Step {i}: {s.get('name', f'Step {i}')}
**Observation:** {s['observation']}
**Action:** {s['action']}
**Tool:** {s['tool']}
**Expected Result:** {s['expected']}
**Success Indicator:** {s['success_indicator']}
**Failure Mode:** {s.get('failure_mode', '—')}""")

    vm = p["verification_method"]
    if isinstance(vm, dict):
        vm_md = "\n\n".join(f"### {k}\n" + "\n".join(f"- {x}" for x in v)
                            for k, v in vm.items())
    else:
        vm_md = str(vm)

    evidence_rows = "\n".join(
        f"| {eid} | — | SUCCESS | see trace |" for eid in (p.get("evidence") or [])) or "| — | — | — | — |"
    prom = p.get("promotion_history") or [[p["promotion_state"], now[:10],
                                           f"{len(p.get('evidence') or [])} verified evidence id(s)"]]

    return f"""---
type: technique
topic: wiki/techniques/_index
source: {(p.get('evidence') or ['unknown'])[0]}
tags: {json.dumps(p['tags'])}
complexity: {p.get('complexity', 'intermediate')}
completeness: complete
last_verified: {now[:10]}
tool_versions: {json.dumps(p.get('tool_versions', []))}
technique_id: {t_id}
name: {p['name']}
category: {p['category']}
problem: "{p['problem']}"
applicable_indicators: {json.dumps(p['applicable_indicators'])}
prerequisites:
  tools: {json.dumps(pre.get('tools', []))}
  environment: {json.dumps(pre.get('environment', []))}
  host_tools: {json.dumps(pre.get('host_tools', []))}
  device_tools: {json.dumps(pre.get('device_tools', []))}
  root_required: {str(bool(pre.get('root_required', False))).lower()}
  emulator_required: {str(bool(pre.get('emulator_required', False))).lower()}
  architecture: {json.dumps(pre.get('architecture', []))}
  android_version_min: {pre.get('android_version_min', 21)}
  android_version_max: {pre.get('android_version_max', 99)}
workflow: "{len(p['workflow'])} steps (see Workflow section)"
decision_points: {json.dumps(p['decision_points'])}
success_indicators: {json.dumps(p['success_indicators'])}
verification_method: "{p.get('verification_summary', 'multi-category gate: structural + content + parser (>=3 categories, zero FAIL)')}"
known_limitations: {json.dumps(p['known_limitations'])}
evidence: {json.dumps(p['evidence'])}
successful_analyses: {json.dumps(p['successful_analyses'])}
failed_analyses: {json.dumps(p['failed_analyses'])}
confidence: {float(p['confidence'])}
promotion_state: {p['promotion_state']}
version: {p.get('version', 1)}
previous_version: {prev}
version_reason: "{p.get('version_reason', 'initial extraction')}"
created_timestamp: {now}
updated_timestamp: {now}
llm_summary: "{p['llm_summary']}"
---

# Technique {t_id}: {p['name']}

## This Article Answers
- "How do I {p['name'].lower()}?"
- "When does technique {t_id} apply?"
- "What are the prerequisites for {t_id}?"

## Key Takeaways
- [PROBLEM] {p['problem']}
- [PREREQUISITES] tools {', '.join(pre.get('tools', [])) or '—'}; root={pre.get('root_required', False)}; env {', '.join(pre.get('environment', [])) or '—'}
- [WORKFLOW] {' -> '.join(s['action'][:40] for s in p['workflow'])}
- [VERIFICATION] {p.get('verification_summary', 'structural + content + parser >=3 categories, zero FAIL')}
- [CONFIDENCE] {float(p['confidence'])} ({p['promotion_state']})

## Problem Statement
- Protection class addressed: `{p.get('protection_class', p['category'])}`
- Why standard approaches fail: {p.get('why_standard_fails', '—')}
- Applicable when: {'; '.join(i.get('indicator', str(i)) if isinstance(i, dict) else str(i) for i in p['applicable_indicators'])}

## Applicable Indicators
| Indicator | Type | Detection Method | Weight |
|---|---|---|---|
{chr(10).join(f"| {i.get('indicator')} | {i.get('type', 'static')} | {i.get('detection', 'inspect')} | {i.get('weight', 'Med')} |" for i in p['applicable_indicators'] if isinstance(i, dict)) or chr(10).join(f"| {i} | static | inspect | Med |" for i in p['applicable_indicators'])}

## Prerequisites
### Required Tools
| Tool ID | Name | Version | Host/Device | Purpose |
|---|---|---|---|---|
{chr(10).join(f"| {t.get('id')} | {t.get('name')} | {t.get('version', 'see registry')} | {t.get('where', 'host')} | {t.get('purpose', '—')} |" for t in (pre.get('tool_details') or [])) or '| see prerequisites.tools | — | — | — | — |'}

### Required Environment
| Requirement | Details |
|---|---|
| Root | {pre.get('root_required', False)} |
| Emulator | {pre.get('emulator_required', False)} |
| Architecture | {', '.join(pre.get('architecture', [])) or 'any'} |
| Android Version | {pre.get('android_version_min', 21)}-{pre.get('android_version_max', 99)} |
| Environment | {', '.join(pre.get('environment', [])) or 'any'} |

## Workflow

{chr(10).join(wf)}

## Decision Points
| Decision Point | Condition | If True | If False |
|---|---|---|---|
{chr(10).join(f"| DP{idx} | {d.get('condition')} | {d.get('if_true')} | {d.get('if_false')} |" for idx, d in enumerate(p['decision_points'], 1)) if p['decision_points'] and isinstance(p['decision_points'][0], dict) else '| DP1 | see llm_summary | proceed | re-plan |'}

## Success Indicators
{chr(10).join(f"- {i}" for i in p['success_indicators'])}

## Verification Method
{vm_md}

**Final Status:** COMMAND_SUCCESS vs VERIFIED_SUCCESS (only VERIFIED_SUCCESS counts for learning)

## Known Failure Conditions
| Condition | Symptom | Workaround |
|---|---|---|
{chr(10).join(f"| {f.get('condition')} | {f.get('symptom')} | {f.get('workaround', 'N/A')} |" for f in (p.get('failure_conditions') or [])) or '| — | — | — |'}

## Limitations
{chr(10).join(f"- {l}" for l in p['known_limitations'])}

## Evidence
| Analysis ID | APK SHA256 | Result | Notes |
|---|---|---|---|
{evidence_rows}

## Successful Analyses
{chr(10).join(f"- {a} — verified success" for a in p['successful_analyses']) or '- none yet'}

## Failed Analyses
{chr(10).join(f"- {a}" for a in p['failed_analyses']) or '- none recorded (failure evidence pending)'}

## Confidence Assessment
| Factor | Score (0-1) | Notes |
|---|---|---|
{chr(10).join(f"| {f.get('factor')} | {f.get('score')} | {f.get('notes', '—')} |" for f in (p.get('confidence_factors') or [])) or f"| **Overall** | {float(p['confidence'])} | see llm_summary |"}

## Promotion History
| State | Date | Evidence |
|---|---|---|
{chr(10).join(f"| {row[0]} | {row[1]} | {row[2]} |" for row in prom)}

## Version History
| Version | Date | Change | Reason |
|---|---|---|---|
{old_rows}{new_row}

## What This Article Does NOT Cover
{chr(10).join(f"- {x}" for x in (p.get('not_covered') or ['behavior outside the recorded evidence APKs / environments']))}

## Open Questions / Unverified Claims
{chr(10).join(f"- {x}" for x in (p.get('open_questions') or ['none']))}

## Related
{chr(10).join(f"- [[wiki/experiments/{e}]] — evidence experiment" for e in (p.get('evidence') or []))}
- [[wiki/success-traces/{p['source_trace']}]] — source success trace
- [[wiki/techniques/_index]] — technique index
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract or version a technique article.")
    ap.add_argument("--payload")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.stdin else Path(args.payload).read_text(encoding="utf-8") if args.payload else ""
    if not raw.strip():
        print(json.dumps({"error": "no payload (use --payload or --stdin)"}))
        return 4
    try:
        p = json.loads(raw)
    except Exception as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}))
        return 4

    tid = p.get("technique_id")
    existing = None
    tech_md = None
    if tid:
        fp = TECHS / f"{tid}.md"
        if fp.exists():
            existing = load_fm(f"techniques/{tid}")
            tech_md = fp.read_text(encoding="utf-8", errors="ignore")

    errs = validate(p, existing)
    if errs:
        print(json.dumps({"error": "validation failed", "problems": errs}, indent=2))
        return 4

    if not tid:
        tid = kb_ids.fmt("T", kb_ids.scan(WIKI).get("T", 0) + 1)
    TECHS.mkdir(parents=True, exist_ok=True)
    path = TECHS / f"{tid}.md"
    if path.exists() and not existing and not p.get("technique_id"):
        print(json.dumps({"error": f"{path.name} already exists - pass technique_id to update"}))
        return 5

    md = render(p, tid, existing, tech_md)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "technique_id": tid, "valid": True,
                          "would_write": str(path)}))
        return 0
    path.write_text(md, encoding="utf-8")
    print(json.dumps({"written": str(path), "technique_id": tid,
                      "version": p.get("version", 1),
                      "promotion_state": p["promotion_state"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
