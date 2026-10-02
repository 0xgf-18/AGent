#!/usr/bin/env python3
"""
Create or update a packer article - packer -> unpacking-method storage
(core reuse mechanism: when a protection is beaten, its full unpacking method
is stored under the packer name so a fresh agent can unpack it again).

Rules enforced:
  - packer_id is a stable slug (a-z, 0-9, -) and names the file; a new packer
    gets its own article, an existing packer_id triggers an update
  - unpacking_status: not_attempted | attempted | unpacked | blocked
  - unpacking_status=unpacked requires >=1 VERIFIED_SUCCESS experiment in
    evidence OR a non-empty documented_in source (no unverified successes)
  - evidence experiment ids must exist
  - unpacking_method steps need name+action; verification needs >=1 check
  - updates require version = previous+1, version_reason, previous_version
    (immutable history - never rewrite old rows)

Usage:
    python record_packer.py --payload p.json [--dry-run]

Exit: 0 written, 4 validation failed, 5 io error.
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "wiki"
PACKERS = WIKI / "packers"

STATUSES = ("not_attempted", "attempted", "unpacked", "blocked")
SLUG_RX = re.compile(r"^[a-z0-9][a-z0-9-]*$")


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


def verified_evidence(exp_ids: list) -> tuple[list, list]:
    """Return (verified_ids, problems) for evidence experiment references."""
    verified, problems = [], []
    for eid in exp_ids or []:
        fm = load_fm(f"experiments/{eid}")
        if fm is None:
            problems.append(f"evidence {eid}: experiment article not found")
        elif fm.get("verification_status") == "VERIFIED_SUCCESS":
            verified.append(eid)
        else:
            problems.append(f"evidence {eid}: verification_status="
                            f"{fm.get('verification_status')!r} (not VERIFIED_SUCCESS)")
    return verified, problems


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "unnamed-packer"


def validate(p: dict, existing: dict | None) -> list[str]:
    errs = []
    for req in ("name", "protection_class", "unpacking_status", "confidence"):
        if p.get(req) in (None, ""):
            errs.append(f"missing required field: {req}")
    for req in ("failure_conditions", "decision_points", "technique_ids",
                "tools", "documented_in", "evidence"):
        if p.get(req) is None:
            errs.append(f"missing required field: {req} (may be empty)")
    if not p.get("indicators"):
        errs.append("missing required field: indicators (non-empty list)")
    if not p.get("unpacking_method"):
        errs.append("missing required field: unpacking_method (non-empty list)")
    if not p.get("verification"):
        errs.append("missing required field: verification (non-empty list)")
    if not p.get("tags"):
        errs.append("missing required field: tags (non-empty list)")

    packer_id = p.get("packer_id") or slugify(p.get("name", ""))
    p["packer_id"] = packer_id
    if not SLUG_RX.match(str(packer_id)):
        errs.append(f"packer_id must match {SLUG_RX.pattern} (got {packer_id!r})")

    status = p.get("unpacking_status")
    if status not in STATUSES:
        errs.append(f"unpacking_status must be one of {STATUSES}")
    try:
        conf = float(p.get("confidence", -1))
        if not 0.0 <= conf <= 1.0:
            errs.append("confidence must be 0.0-1.0")
    except (TypeError, ValueError):
        errs.append("confidence must be numeric 0.0-1.0")

    verified, problems = verified_evidence(p.get("evidence"))
    errs.extend(problems)
    if status == "unpacked" and not verified and not (p.get("documented_in") or "").strip():
        errs.append("unpacking_status=unpacked requires >=1 VERIFIED_SUCCESS "
                    "experiment in evidence OR non-empty documented_in")

    for i, s in enumerate(p.get("unpacking_method") or [], 1):
        if not isinstance(s, dict):
            if not str(s).strip():
                errs.append(f"unpacking_method step {i} is empty")
            continue
        missing = [k for k in ("name", "action") if not s.get(k)]
        if missing:
            errs.append(f"unpacking_method step {i} missing {missing} (name+action required)")

    if existing:
        old_v = int(existing.get("version", 1))
        new_v = p.get("version")
        if new_v != old_v + 1:
            errs.append(f"version must be {old_v + 1} for an update (got {new_v})")
        if not p.get("version_reason"):
            errs.append("updates require version_reason (version history immutable)")
        if not p.get("previous_version"):
            errs.append("updates require previous_version: "
                        f"'{existing.get('packer_id')} v{old_v}'")
    else:
        if p.get("version", 1) != 1:
            errs.append("new packer must start at version 1")
    return errs


def _fmt_check(v) -> str:
    if isinstance(v, dict):
        return (f"| {v.get('category', '—')} | {v.get('check', '—')} "
                f"| {v.get('pass_condition', '—')} |")
    return f"| — | {v} | — |"


def render(p: dict, existing: dict | None, old_md: str | None) -> str:
    now = p.get("created_timestamp") or dt.datetime.now().isoformat(timespec="seconds")
    prev = p.get("previous_version", "")
    old_rows = ""
    if existing and old_md:
        m = re.search(r"## Version History\n\|[^\n]*\n\|[-| ]+\|\n((?:\|[^\n]*\n)+)", old_md)
        if m:
            old_rows = m.group(1).rstrip("\n") + "\n"
    new_row = (f"| {p.get('version', 1)} | {now[:10]} | "
               f"{p.get('change_summary', 'Update')} | "
               f"{p.get('version_reason', 'initial recording')} |")

    indicators = p.get("indicators") or []
    ind_rows = []
    for i in indicators:
        if isinstance(i, dict):
            ind_rows.append(f"| {i.get('indicator')} | {i.get('where', '—')} "
                            f"| {i.get('detect', 'inspect')} |")
        else:
            ind_rows.append(f"| {i} | static | inspect |")
    ind_md = "\n".join(ind_rows) or "| — | — | — |"

    steps = []
    for i, s in enumerate(p.get("unpacking_method") or [], 1):
        if isinstance(s, dict):
            head = f"### Step {i}: {s.get('name', f'Step {i}')}"
            obs = f"**Observation:** {s['observation']}\n" if s.get("observation") else ""
            steps.append(f"{head}\n{obs}**Action:** {s['action']}\n"
                         f"**Tool:** {s.get('tool', '—')}\n"
                         f"**Expected:** {s.get('expected', '—')}\n"
                         f"**Success Indicator:** {s.get('success_indicator', '—')}\n"
                         f"**Failure Mode:** {s.get('failure_mode', '—')}")
        else:
            steps.append(f"### Step {i}\n{s}")
    steps_md = "\n\n".join(steps)

    ver_md = "\n".join(_fmt_check(v) for v in (p.get("verification") or []))
    dp = p.get("decision_points") or []
    if dp and isinstance(dp[0], dict):
        dp_md = "\n".join(f"| {d.get('condition')} | {d.get('if_true')} | {d.get('if_false')} |"
                          for d in dp)
    else:
        dp_md = "\n".join(f"| {d} | — | — |" for d in dp)
    fails = p.get("failure_conditions") or []
    if fails and isinstance(fails[0], dict):
        fail_md = "\n".join(f"| {f.get('condition')} | {f.get('symptom')} "
                            f"| {f.get('workaround', '—')} |" for f in fails)
    else:
        fail_md = "\n".join(f"| {f} | — | — |" for f in fails)
    return _render_tail(p, existing, old_md, now, prev, old_rows, new_row,
                        ind_md, steps_md, ver_md, dp_md, fail_md)
    # (tail in _render_tail below)


def _render_tail(p, existing, old_md, now, prev, old_rows, new_row,
                 ind_md, steps_md, ver_md, dp_md, fail_md) -> str:
    status = p.get("unpacking_status")
    if status == "unpacked":
        status_line = "`unpacked` — verified on at least one APK (see Evidence)"
    else:
        status_line = f"`{status}` — {p.get('status_note', '')}".rstrip()
    evidence_rows = "\n".join(
        f"| {eid} | VERIFIED | see experiment article |"
        for eid in (p.get("evidence") or [])) or "| — | — | — |"

    related = ["- [[wiki/techniques/apk-unpacking-playbook]] — playbook with verbatim commands",
               "- [[wiki/packers/_index]] — packer index"]
    related += [f"- [[wiki/experiments/{e}]] — evidence experiment"
                for e in (p.get("evidence") or [])]
    for t in (p.get("technique_ids") or []):
        related.append(f"- [[wiki/techniques/{t}]] — technique")

    src = p.get("documented_in") or (p.get("evidence") or ["unknown"])[0]
    aliases = p.get("aliases") or []
    first_p = p.get("first_seen") or now[:10]
    takeaways_rec = "; ".join(
        str(i.get("indicator", i)) if isinstance(i, dict) else str(i)
        for i in (p.get("indicators") or [])[:3])
    takeaways_meth = " -> ".join(
        (s.get("name", s.get("action", ""))[:48] if isinstance(s, dict) else str(s)[:48])
        for s in (p.get("unpacking_method") or []))
    evidence_line = (", ".join(p.get("evidence") or [])
                     or p.get("documented_in") or "none recorded")

    head = f"""---
type: packer
topic: wiki/packers/_index
source: {src}
tags: {json.dumps(p['tags'])}
complexity: {p.get('complexity', 'advanced')}
completeness: {p.get('completeness', 'complete')}
last_verified: {now[:10]}
packer_id: {p['packer_id']}
name: "{p['name']}"
aliases: {json.dumps(aliases)}
protection_class: {p.get('protection_class', 'packer')}
first_seen: {first_p}
indicators: {json.dumps(p['indicators'])}
unpacking_status: {status}
confidence: {float(p['confidence'])}
evidence: {json.dumps(p.get('evidence') or [])}
technique_ids: {json.dumps(p.get('technique_ids') or [])}
tools: {json.dumps(p.get('tools') or [])}
documented_in: "{src}"
version: {p.get('version', 1)}
previous_version: {prev}
version_reason: "{p.get('version_reason', 'initial recording')}"
created_timestamp: {now}
updated_timestamp: {now}
llm_summary: "{p['llm_summary']}"
---

# Packer: {p['name']}

## This Article Answers
- "How do I recognize {p['name']} on an APK?"
- "How do I unpack {p['name']}?"
- "What is verified for this packer and what is still unverified?"

## Key Takeaways
- [RECOGNIZE] {takeaways_rec}
- [METHOD] {takeaways_meth}
- [STATUS] {status_line}
- [CONFIDENCE] {float(p['confidence'])}
- [EVIDENCE] {evidence_line}

## Identification
| Indicator | Where | How to detect |
|---|---|---|
{ind_md}

## Unpacking Status
- **Status:** {status}
- **Documented in:** {p.get('documented_in') or '—'}
- **Techniques:** {', '.join(p.get('technique_ids') or []) or '—'}
- **Tools:** {', '.join(p.get('tools') or []) or '—'}

## Unpacking Method
{steps_md}

## Decision Points
| Condition | If True | If False |
|---|---|---|
{dp_md or '| — | — | — |'}

## Verification
| Category | Check | Pass condition |
|---|---|---|
{ver_md}

## Known Failure Conditions
| Condition | Symptom | Workaround |
|---|---|---|
{fail_md or '| — | — | — |'}

## Evidence
| Experiment | Result | Notes |
|---|---|---|
{evidence_rows}

## Version History
| Version | Date | Change | Reason |
|---|---|---|---|
{old_rows}{new_row}

## What This Article Does NOT Cover
{chr(10).join('- ' + str(x) for x in (p.get('not_covered') or ['variants not covered by the recorded evidence']))}

## Related
{chr(10).join(related)}
"""
    return head


def main() -> int:
    ap = argparse.ArgumentParser(description="Create or update a packer article.")
    ap.add_argument("--payload")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.stdin else ""
    if not raw.strip() and args.payload:
        raw = Path(args.payload).read_text(encoding="utf-8")
    if not raw.strip():
        print(json.dumps({"error": "no payload (use --payload or --stdin)"}))
        return 4
    try:
        p = json.loads(raw)
    except Exception as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}))
        return 4

    packer_id = p.get("packer_id") or slugify(p.get("name", ""))
    p["packer_id"] = packer_id
    path = PACKERS / f"{packer_id}.md"
    existing, old_md = None, None
    if path.exists():
        existing = load_fm(f"packers/{packer_id}")
        old_md = path.read_text(encoding="utf-8", errors="ignore")

    errs = validate(p, existing)
    if errs:
        print(json.dumps({"error": "validation failed", "problems": errs}, indent=2))
        return 4

    md = render(p, existing, old_md)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "packer_id": packer_id, "valid": True,
                          "action": "update" if existing else "create",
                          "would_write": str(path)}))
        return 0
    PACKERS.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")
    print(json.dumps({"written": str(path), "packer_id": packer_id,
                      "action": "update" if existing else "create",
                      "version": p.get("version", 1),
                      "unpacking_status": p["unpacking_status"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
