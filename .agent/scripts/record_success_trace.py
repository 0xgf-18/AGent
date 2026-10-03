#!/usr/bin/env python3
"""
Record a success trace — Phase 4 of the research loop
(see .kb/schemas/success-trace.md).

ONLY traces backed by a VERIFIED_SUCCESS experiment are accepted:
  - the referenced experiment article must exist in the wiki and its
    verification_status must be VERIFIED_SUCCESS (anti-fake check)
  - verification_categories must be a subset of the experiment's categories
  - >=3 PASS verification rows, mandatory before/after + reproducibility fields
  - causality factors carry a provenance mark ([V] / [I] / [U] / [AI Synthesis]);
    causality_analysis may only be SUPPORTED when every ESSENTIAL factor is [V]
    with experiment evidence.

Usage:
    python record_success_trace.py --payload st.json [--dry-run]

Exit: 0 written, 4 validation failed, 5 io error.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_ids  # noqa: E402

WIKI = Path(__file__).resolve().parent.parent.parent / "vault" / "articles"
TRACES = WIKI / "success-traces"
GATE_CATEGORIES = {"STRUCTURAL", "PARSER", "CONTENT", "DOWNSTREAM", "REPRODUCIBILITY",
                   "DOWNSTREAM_ANALYSIS"}
MARKS = ("V", "I", "U", "AI Synthesis")
CAUSAL_CLASSES = ("ESSENTIAL", "LIKELY_RELEVANT", "OPTIONAL", "IRRELEVANT")


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


def find_experiment(exp_id: str) -> tuple[dict | None, str]:
    p = WIKI / "experiments" / f"{exp_id}.md"
    if not p.exists():
        return None, f"experiment article not found: {exp_id}"
    fm = load_fm(f"experiments/{exp_id}")
    if not fm:
        return None, f"cannot parse {p.name}"
    if fm.get("verification_status") != "VERIFIED_SUCCESS":
        return None, (f"{exp_id} verification_status is "
                      f"{fm.get('verification_status')!r}, not VERIFIED_SUCCESS - "
                      "a trace may only be built from verified successes")
    return fm, ""


def validate(p: dict) -> list[str]:
    errs = []
    for req in ("analysis_id", "experiment_id", "input_sha256", "environment_id",
                "techniques_used", "tools_used", "verification_categories",
                "confidence", "causality_analysis", "goal", "llm_summary",
                "steps", "verification_table", "before_after", "reproducibility",
                "causality", "failed_attempts_note"):
        if p.get(req) is None or p.get(req) == "":
            errs.append(f"missing required field: {req}")
    if p.get("final_result", "VERIFIED_SUCCESS") != "VERIFIED_SUCCESS":
        errs.append("final_result must be VERIFIED_SUCCESS (schema rule)")
    try:
        conf = float(p.get("confidence", -1))
        if not 0.0 <= conf <= 1.0:
            errs.append("confidence must be 0.0-1.0")
    except (TypeError, ValueError):
        errs.append("confidence must be numeric 0.0-1.0")
    if p.get("causality_analysis") not in ("INFERENCE", "SUPPORTED"):
        errs.append("causality_analysis must be INFERENCE or SUPPORTED")

    # source experiment cross-check (anti-fake)
    exp_fm, err = find_experiment(p.get("experiment_id", ""))
    if err:
        errs.append(err)
    else:
        exp_cats = set(exp_fm.get("verification_categories") or [])
        got = set(p.get("verification_categories") or [])
        unknown = got - GATE_CATEGORIES
        if unknown:
            errs.append(f"unknown verification categories: {sorted(unknown)}")
        if len(got & GATE_CATEGORIES) < 3:
            errs.append("verification_categories needs >=3 gate categories")
        if exp_cats and not got.issubset(exp_cats):
            errs.append(f"categories {sorted(got - exp_cats)} not present in {p['experiment_id']} "
                        f"({sorted(exp_cats)})")

    vt = p.get("verification_table") or []
    passes = [r for r in vt if r.get("status") == "PASS"]
    if len({r.get("category") for r in passes}) < 3:
        errs.append("verification_table needs >=3 distinct PASS categories")
    if any(r.get("status") != "PASS" for r in vt):
        errs.append("verification_table contains FAIL rows - trace requires all PASS")

    if not isinstance(p.get("steps"), list) or not p["steps"]:
        errs.append("steps must be a non-empty list")
    if not isinstance(p.get("before_after"), list) or not p["before_after"]:
        errs.append("before_after must be a non-empty list (schema: mandatory)")
    repro = p.get("reproducibility") or {}
    if not repro.get("performed"):
        errs.append("reproducibility.performed must be set")
    fa = p.get("failed_attempts") or []
    if not fa and not p.get("failed_attempts_note"):
        errs.append("failed_attempts is empty - provide failed_attempts_note explaining why")

    caus = p.get("causality") or {}
    essential = caus.get("ESSENTIAL") or []
    if not essential:
        errs.append("causality.ESSENTIAL must have at least one factor")
    for cls, factors in caus.items():
        if cls not in CAUSAL_CLASSES:
            errs.append(f"unknown causality class: {cls}")
            continue
        for f in factors:
            for k in ("factor", "evidence", "mark", "confidence"):
                if k not in f:
                    errs.append(f"causality {cls} factor missing '{k}': {f}")
            if f.get("mark") not in MARKS:
                errs.append(f"causality mark must be one of {MARKS}: {f.get('factor')}")
    if p.get("causality_analysis") == "SUPPORTED":
        bad = [f for f in essential if f.get("mark") != "V" or not f.get("evidence")]
        if bad:
            errs.append("causality SUPPORTED requires every ESSENTIAL factor marked [V] "
                        f"with experiment evidence: {[b.get('factor') for b in bad]}")
    return errs


def render(p: dict, st_id: str) -> str:
    ts = p.get("timestamp") or dt.datetime.now().isoformat(timespec="seconds")
    exp_fm, _ = find_experiment(p["experiment_id"])
    exp_fm = exp_fm or {}

    steps_md = []
    for i, s in enumerate(p["steps"], 1):
        steps_md.append(f"""### Step {i}
**Observation:** {s.get('observation', '—')}
**Action:** {s.get('action')}
**Tool:** {s.get('tool', '—')} (version: `{s.get('tool_version', 'see registry')}`)
**Host/Device:** {s.get('host_device', 'host')}
**Command:** `{s.get('command', s.get('action'))}`
**Duration:** {s.get('duration', '—')}
**Result:** {s.get('result', '—')}
**Success Indicator Observed:** {s.get('indicator', '—')}
**Artifacts Produced:** {', '.join(s.get('artifacts', [])) or '—'}""")

    fail_md = []
    for i, a in enumerate(p.get("failed_attempts") or [], 1):
        fail_md.append(f"""### Attempt {i} ({a.get('id', f'{p["experiment_id"]}-FAIL-{i}')})
**Technique:** {a.get('technique', '—')}
**Tools:** {', '.join(a.get('tools', [])) or '—'}
**Action:** {a.get('action', '—')}
**Result:** {a.get('result', 'FAILED')}
**Failure Reason:** {a.get('reason', '—')}
**Observation:** {a.get('observation', '—')}
**Why It Matters:** {a.get('why_it_matters', '—')}""")
    if not fail_md:
        fail_md = [f"_No failed attempts preceded this success:_ {p['failed_attempts_note']}_"]

    vt_md = "\n".join(f"| {r.get('category')} | {r.get('check')} | {r.get('expected')} "
                      f"| {r.get('actual')} | {r.get('status')} |"
                      for r in p["verification_table"])

    def caus_tables() -> str:
        out = []
        for cls in CAUSAL_CLASSES:
            factors = (p.get("causality") or {}).get(cls) or []
            rows = "\n".join(
                f"| {f.get('factor')} | [{f.get('mark')}] {f.get('evidence')} | {f.get('confidence')} |"
                for f in factors) or "| — | — | — |"
            out.append(f"### {cls}\n| Factor | Evidence | Confidence |\n|---|---|---|\n{rows}")
        return "\n\n".join(out)

    ba_md = "\n".join(f"| {r.get('property')} | {r.get('input', '—')} | {r.get('intermediate', '—')} "
                      f"| {r.get('output', '—')} |" for r in p["before_after"])
    repro = p.get("reproducibility") or {}
    fails = p.get("failed_attempts") or []
    extract = p.get("extracted_technique") or "pending"
    kd = p.get("knowledge_diff_id") or "pending (Phase 5)"

    return f"""---
type: success-trace
topic: wiki/success-traces/_index
source: {p['experiment_id']}
tags: {json.dumps(p.get('tags', ['success-trace']))}
complexity: {p.get('complexity', 'advanced')}
completeness: complete
last_verified: {ts[:10]}
tool_versions: {json.dumps(p.get('tool_versions', []))}
success_trace_id: {st_id}
analysis_id: {p['analysis_id']}
experiment_id: {p['experiment_id']}
input_sha256: {p['input_sha256']}
environment_id: {p['environment_id']}
techniques_used: {json.dumps(p['techniques_used'])}
tools_used: {json.dumps(p['tools_used'])}
final_result: VERIFIED_SUCCESS
verification_categories: {json.dumps(sorted(set(p['verification_categories'])))}
confidence: {float(p['confidence'])}
causality_analysis: {p['causality_analysis']}
llm_summary: "{p['llm_summary']}"
---

# Success Trace {st_id}

## This Article Answers
- "What exactly led to success in analysis {p['analysis_id']}?"
- "Which factors were essential vs incidental?"
- "Can this workflow be reproduced?"

## Key Takeaways
- [SUCCESS] {p['goal']}
- [ESSENTIAL_FACTORS] {'; '.join(f.get('factor', '') for f in (p.get('causality') or {}).get('ESSENTIAL', []))}
- [WORKFLOW] {' -> '.join(str(s.get('action', ''))[:40] for s in p['steps'][:5])}
- [VERIFICATION] {', '.join(sorted(set(p['verification_categories'])))}
- [CONFIDENCE] {float(p['confidence'])} ({p['causality_analysis']})

## Context
| Property | Value |
|---|---|
| Analysis ID | {p['analysis_id']} |
| Experiment ID | {p['experiment_id']} |
| Input APK SHA256 | `{p['input_sha256']}` |
| Environment | `{p['environment_id']}` |
| Date | {ts[:10]} |

## Environment Profile (Snapshot at Time of Success)
> Environment: {p['environment_id']} (probed live via env_probe.py --health; never stored)
{p.get('environment_snapshot', '- runtime-only; run env_probe.py --health for the live profile (never stored)')}

## Experiment Sequence

{chr(10).join(steps_md)}

## Failed Attempts Before Success
> These attempts immediately preceded the successful workflow and provide critical context.

{chr(10).join(fail_md)}

## Final Result Verification
| Category | Check | Expected | Actual | Status |
|---|---|---|---|---|
{vt_md}

**Overall:** VERIFIED_SUCCESS

## Success Causality Analysis
> **Marked as INFERENCE until supported by additional experiments.**

{caus_tables()}

**Causality Status:** {p['causality_analysis']}

## Extracted Technique
> **Reference:** [[wiki/techniques/{extract}]] if created
**Technique ID:** {extract}
**Generalized From:** This specific success trace
**Abstraction Level:** {p.get('abstraction_level', 'specific commands kept verbatim; environment/tool ids generalized')}

## Artifacts Produced
| Artifact ID | Type | Hash | Size | Location | Verified | Downstream Usable |
|---|---|---|---|---|---|---|
{chr(10).join(f"| {a.get('artifact_id')} | {a.get('type')} | `{a.get('hash')}` | {a.get('size')} | `{a.get('location')}` | {a.get('verified')} | {a.get('downstream', a.get('verified'))} |" for a in (p.get('artifacts') or [])) or '| — | — | — | — | — | — | — |'}

## Before/After Comparison
| Property | Input (APK) | Intermediate | Output (Final) |
|---|---|---|---|
{ba_md}

## Reproducibility Test
**Performed:** {repro.get('performed')}
**Date:** {repro.get('date', ts[:10])}
**Result:** {repro.get('result', '—')}
**Notes:** {repro.get('notes', '—')}

## Knowledge Diff Generated
> References: [[wiki/knowledge-diffs/{kd}]]
{chr(10).join('- ' + line for line in (p.get('knowledge_changes') or ['NEW: technique extraction pending']))}

## What This Article Does NOT Cover
- Techniques not present in the linked experiment records
- Behavior outside {p['environment_id']} (environment-specific caveats untested elsewhere)

## Open Questions / Unverified Claims
{chr(10).join('- causality factors marked [I]/[U]/[AI Synthesis]: ' + ', '.join(
    f.get('factor', '?') for cls in CAUSAL_CLASSES
    for f in (p.get('causality') or {}).get(cls, []) if f.get('mark') != 'V')
) or '- none (all ESSENTIAL factors [V])'}

## Related
- [[wiki/apks/{p['analysis_id']}]] — source analysis
- [[wiki/experiments/{p['experiment_id']}]] — source experiment
- [[wiki/techniques/{extract}]] — extracted/updated technique
- environment: {p['environment_id']} (runtime-only, never stored)
- [[wiki/success-traces/_index]] — trace index
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Record a success trace (VERIFIED_SUCCESS only).")
    ap.add_argument("--payload", help="path to JSON payload")
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

    errs = validate(p)
    if errs:
        print(json.dumps({"error": "validation failed", "problems": errs}, indent=2))
        return 4

    st_id = p.get("success_trace_id") or kb_ids.fmt("ST", kb_ids.scan(WIKI).get("ST", 0) + 1)
    TRACES.mkdir(parents=True, exist_ok=True)
    path = TRACES / f"{st_id}.md"
    if path.exists() and not p.get("success_trace_id"):
        print(json.dumps({"error": f"{path.name} already exists - pass success_trace_id to update"}))
        return 5
    md = render(p, st_id)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "success_trace_id": st_id, "valid": True,
                          "would_write": str(path)}))
        return 0
    path.write_text(md, encoding="utf-8")
    print(json.dumps({"written": str(path), "success_trace_id": st_id,
                      "experiment_id": p["experiment_id"],
                      "causality_analysis": p["causality_analysis"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
