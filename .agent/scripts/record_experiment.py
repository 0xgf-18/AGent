#!/usr/bin/env python3
"""
Record an experiment — Phase 3 of the research loop
(see .kb/schemas/experiment.md and .kb/experiment-protocol.md section 3).

Reads a JSON payload (file or stdin), validates it against the schema rules,
allocates the next EXP-XXXX id (never reused) and writes
knowledge_base/wiki/experiments/EXP-XXXX.md.

Validation refuses to write when:
  - required fields are missing (steps, learning, toolset, environment, ...)
  - result is FAILURE but failure_category is missing
  - verification_status is VERIFIED_SUCCESS but fewer than 3 verification
    categories were provided, or result is FAILURE

Usage:
    python record_experiment.py --payload exp.json
    type exp.json | python record_experiment.py --stdin
    python record_experiment.py --payload exp.json --dry-run    # validate only

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

WIKI = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "wiki"
EXPERIMENTS = WIKI / "experiments"

VALID_RESULTS = ("SUCCESS", "PARTIAL", "FAILURE")
VALID_VERIFICATION = ("UNVERIFIED", "COMMAND_SUCCESS", "VERIFIED_SUCCESS")
VALID_FAILURE_CATEGORIES = ("TECHNIQUE", "TOOL", "ENVIRONMENT", "APK", "VERIFICATION", "UNKNOWN")
GATE_CATEGORIES = ("STRUCTURAL", "PARSER", "CONTENT", "DOWNSTREAM", "REPRODUCIBILITY")


def validate(p: dict) -> list[str]:
    errs = []
    for req in ("analysis_id", "technique_id", "toolset", "environment_id",
                "input_fingerprint", "result", "verification_status",
                "steps", "learning", "key_learning", "notes"):
        if not p.get(req):
            errs.append(f"missing required field: {req}")
    if p.get("result") not in VALID_RESULTS:
        errs.append(f"result must be one of {VALID_RESULTS}")
    if p.get("verification_status") not in VALID_VERIFICATION:
        errs.append(f"verification_status must be one of {VALID_VERIFICATION}")
    if p.get("result") == "FAILURE" and p.get("failure_category") not in VALID_FAILURE_CATEGORIES:
        errs.append(f"FAILURE requires failure_category one of {VALID_FAILURE_CATEGORIES}")
    cats = p.get("verification_categories") or []
    if p.get("verification_status") == "VERIFIED_SUCCESS":
        if p.get("result") == "FAILURE":
            errs.append("VERIFIED_SUCCESS is impossible for a FAILURE experiment")
        bad = [c for c in cats if c not in GATE_CATEGORIES]
        if bad:
            errs.append(f"unknown verification categories: {bad}")
        if len(set(cats)) < 3:
            errs.append(f"VERIFIED_SUCCESS requires >=3 distinct categories, got {len(set(cats))}")
    if p.get("result") in ("SUCCESS", "PARTIAL") and p.get("verification_status") == "UNVERIFIED":
        errs.append("SUCCESS/PARTIAL must be verified (COMMAND_SUCCESS or VERIFIED_SUCCESS) "
                    "before recording - run verify_result.py first")
    if isinstance(p.get("steps"), list) and not p["steps"]:
        errs.append("steps must contain at least one step")
    for s in (p.get("steps") or []):
        if not (isinstance(s, dict) and s.get("action")):
            errs.append("every step needs an 'action' (verbatim)")
    return errs


def artifact_rows(p: dict) -> list[dict]:
    arts = p.get("artifacts") or []
    start = kb_ids.scan(WIKI).get("ART", 0)
    out = []
    for i, a in enumerate(arts, 1):
        aid = a.get("artifact_id") or f"ART-{start + i:04d}"
        out.append({"artifact_id": aid, "type": a.get("type", "OTHER"),
                    "hash": a.get("hash", "—"), "size": a.get("size", "—"),
                    "location": a.get("location", "—"), "verified": a.get("verified", "No")})
    return out


def render(p: dict, exp_id: str, ts: str, arts: list[dict]) -> str:
    steps_md = []
    for i, s in enumerate(p["steps"], 1):
        steps_md.append(f"""### Step {i}
**Observation:** {s.get('observation', '—')}
**Action:** {s.get('action')}
**Tool:** {s.get('tool', '—')} (version: `{s.get('tool_version', 'see registry')}`)
**Host/Device:** {s.get('host_device', 'host')}
**Command/Script:** `{s.get('command', s.get('action'))}`
**Input:** {s.get('input', '—')}
**Expected:** {s.get('expected', '—')}
**Actual Result:** {s.get('actual', '—')}
**Duration:** {s.get('duration', '—')}
**Output Artifacts:** {', '.join(a['artifact_id'] for a in arts) or '[]'}
**Success Indicators Observed:** {', '.join(s.get('indicators', [])) or '—'}
""")
    obs = p.get("observations") or []
    obs_md = "\n".join(f"| {o.get('step', i)} | {o.get('observation', '—')} | {o.get('significance', '—')} |"
                       for i, o in enumerate(obs, 1)) or "| — | — | — |"
    art_md = "\n".join(f"| {a['artifact_id']} | {a['type']} | `{a['hash']}` | {a['size']} "
                       f"| `{a['location']}` | {a['verified']} |" for a in arts) or "| — | — | — | — | — | — |"
    prereq = p.get("prerequisites") or [{"requirement": "see protocol", "required": "—",
                                         "available": "—", "met": "—"}]
    pre_md = "\n".join(f"| {r.get('requirement')} | {r.get('required')} | {r.get('available')} "
                       f"| {r.get('met')} |" for r in prereq)
    ba = p.get("before_after") or []
    ba_md = "\n".join(f"| {r.get('property')} | {r.get('before')} | {r.get('after')} |" for r in ba) \
        or "| — | — | — |"
    L = p["learning"]
    fail_block = ""
    if p.get("result") == "FAILURE":
        fail_block = f"""
## Failure Information
**Failure Category:** {p.get('failure_category')}
**Detailed Reason:** {p.get('failure_detail', p.get('notes'))}
**Known Issue:** {p.get('known_issue', 'No')}
**Workaround Attempted:** {p.get('workaround', '—')}
**Next Technique to Try:** {p.get('next_technique', 'exploratory')}
"""
    success_block = ""
    if p.get("result") in ("SUCCESS", "PARTIAL"):
        success_block = f"""
### Success Details
**Success Indicators Met:** {', '.join(p.get('success_indicators', [])) or '—'}
**Verification Performed:** {', '.join(p.get('verification_categories', [])) or '—'}
**Gate Reason:** {p.get('gate_reason', '—')}
**Downstream Usable:** {p.get('downstream_usable', 'Yes')}
"""
    return f"""---
type: experiment
topic: wiki/experiments/_index
source: {p['analysis_id']}
tags: {json.dumps(p.get('tags', ['experiment']))}
complexity: {p.get('complexity', 'intermediate')}
completeness: complete
last_verified: {ts[:10]}
tool_versions: {json.dumps(p.get('tool_versions', []))}
experiment_id: {exp_id}
analysis_id: {p['analysis_id']}
technique_id: {p['technique_id']}
toolset: {json.dumps(p['toolset'])}
environment_id: {p['environment_id']}
input_fingerprint: "{p['input_fingerprint']}"
timestamp: {ts}
steps: {len(p['steps'])}
result: {p['result']}
verification_status: {p['verification_status']}
failure_category: {p.get('failure_category') or 'N/A'}
notes: {json.dumps(p['notes'])}
key_learning: {json.dumps(p['key_learning'])}
llm_summary: {json.dumps(p['llm_summary'])}
---

# Experiment {exp_id}

## This Article Answers
- "What was attempted in this experiment?"
- "What was the result?"
- "What was learned (success or failure)?"

## Key Takeaways
- [APPROACH] {p['technique_id']} — {p.get('hypothesis', p['notes'])}
- [TOOLS] {', '.join(p['toolset'])}
- [RESULT] {p['result']} ({p['verification_status']})
- [LEARNING] {p['key_learning']}

## Context
| Property | Value |
|---|---|
| Experiment ID | {exp_id} |
| Analysis ID | {p['analysis_id']} |
| Technique | {p['technique_id']} |
| Environment | `{p['environment_id']}` |
| Timestamp | {ts} |
| Input APK | `{p['input_fingerprint']}` |

## Prerequisites Check
| Requirement | Required | Available | Met |
|---|---|---|---|
{pre_md}

**Prerequisites Met:** {p.get('prerequisites_met', 'ALL')}

## Steps
{chr(10).join(steps_md)}
## Observations
| Step | Observation | Significance |
|---|---|---|
{obs_md}

## Artifacts Produced
| Artifact ID | Type | Hash | Size | Location | Verified |
|---|---|---|---|---|---|
{art_md}

## Result
**Status:** {p['result']}
**Verification:** {p['verification_status']}
**Failure Category (if failed):** {p.get('failure_category') or 'N/A'}
{success_block}{fail_block}
## Before/After Comparison
| Property | Before | After |
|---|---|---|
{ba_md}

## Learning Extracted
- **What worked:** {L.get('worked', '—')}
- **What didn't work:** {L.get('not_worked', '—')}
- **Environment sensitivity:** {L.get('environment_sensitivity', '—')}
- **Tool version sensitivity:** {L.get('tool_version_sensitivity', '—')}
- **New indicators discovered:** {', '.join(L.get('new_indicators', [])) or '—'}
- **Refined applicability for technique:** {L.get('refined_applicability', '—')}

## Related
- [[wiki/apks/{p['analysis_id']}]] — parent analysis
- [[wiki/techniques/apk-unpacking-playbook]] — technique catalog ({p['technique_id']})
- environment: {p['environment_id']} (probed live via env_probe.py --health; never stored)
- [[wiki/experiments/_index]] — experiment index
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Record an experiment article.")
    ap.add_argument("--payload", help="path to JSON payload")
    ap.add_argument("--stdin", action="store_true", help="read JSON payload from stdin")
    ap.add_argument("--dry-run", action="store_true", help="validate only, do not write")
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

    errs = validate(p)
    if errs:
        print(json.dumps({"error": "validation failed", "problems": errs}, indent=2))
        return 4

    ts = p.get("timestamp") or dt.datetime.now().isoformat(timespec="seconds")
    exp_id = p.get("experiment_id") or kb_ids.fmt("EXP", kb_ids.scan(WIKI).get("EXP", 0) + 1)
    arts = artifact_rows(p)

    # collision guard (never overwrite an existing experiment)
    EXPERIMENTS.mkdir(parents=True, exist_ok=True)
    path = EXPERIMENTS / f"{exp_id}.md"
    if path.exists() and not p.get("experiment_id"):
        print(json.dumps({"error": f"{path.name} already exists - rerun allocation"}))
        return 5

    md = render(p, exp_id, ts, arts)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "experiment_id": exp_id, "valid": True,
                          "would_write": str(path), "steps": len(p["steps"])}))
        return 0
    path.write_text(md, encoding="utf-8")
    print(json.dumps({"written": str(path), "experiment_id": exp_id,
                      "result": p["result"], "verification_status": p["verification_status"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
