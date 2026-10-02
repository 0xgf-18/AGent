#!/usr/bin/env python3
"""
Phase 4 smoke test — success traces + technique extraction/versioning:

  1. record_success_trace refuses trace on missing experiment (exit 4)
  2. record_success_trace refuses final_result != VERIFIED_SUCCESS (exit 4)
  3. record_success_trace refuses causality SUPPORTED with non-[V] ESSENTIAL (exit 4)
  4. record_success_trace refuses <3 PASS verification rows (exit 4)
  5. record_success_trace valid dry-run (exit 0)
  6. ST-0001 article: schema fields, final_result VERIFIED, causality INFERENCE
  7. record_technique refuses TRUSTED with 1 verified evidence (exit 4)
  8. record_technique refuses update without version bump (exit 4)
  9. record_technique refuses workflow step missing Success Indicator (exit 4)
 10. record_technique valid dry-run new technique (exit 0)
 11. T-0020 article: schema fields, CANDIDATE, evidence EXP-0001, version 1
 12. kb_search returns T-0020 top-ranked with prereqs MET (runtime fallback gate)
 13. success-trace cross index contains ST-0001

Run:  python .kb/scripts/tests/test_phase4.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
REPO = SCRIPTS.parent.parent
WIKI = REPO / "knowledge_base" / "wiki"

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def run(args, timeout=120):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace", cwd=REPO)
    return p.returncode, (p.stdout + p.stderr).strip()


def last_json(out: str) -> dict:
    try:
        v = json.loads(out)
        if isinstance(v, dict):
            return v
    except Exception:
        pass
    for ln in reversed(out.splitlines()):
        s = ln.strip()
        if s.startswith("{"):
            try:
                return json.loads(ln)
            except Exception:
                continue
    return {}


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="phase4_"))
    rst = str(SCRIPTS / "record_success_trace.py")
    rtech = str(SCRIPTS / "record_technique.py")

    base_st = {
        "success_trace_id": "ST-9999",
        "analysis_id": "A-000001",
        "experiment_id": "EXP-0001",
        "input_sha256": "2481b4e4" + "0" * 56,
        "environment_id": "host-runtime",
        "techniques_used": ["T-0008"],
        "tools_used": ["TR-0007"],
        "final_result": "VERIFIED_SUCCESS",
        "verification_categories": ["STRUCTURAL", "PARSER", "CONTENT"],
        "confidence": 0.5,
        "causality_analysis": "INFERENCE",
        "goal": "g", "llm_summary": "s", "failed_attempts_note": "n/a",
        "steps": [{"observation": "o", "action": "a", "tool": "t",
                   "expected": "e", "indicator": "i"}],
        "verification_table": [
            {"category": "STRUCTURAL", "check": "c", "expected": "x", "actual": "y", "status": "PASS"},
            {"category": "PARSER", "check": "c", "expected": "x", "actual": "y", "status": "PASS"},
            {"category": "CONTENT", "check": "c", "expected": "x", "actual": "y", "status": "PASS"},
        ],
        "before_after": [{"property": "SHA256", "input": "a", "intermediate": "b", "output": "c"}],
        "reproducibility": {"performed": True, "date": "2026-09-29", "result": "SUCCESS", "notes": "n"},
        "causality": {"ESSENTIAL": [{"factor": "f", "evidence": "e", "mark": "V",
                                     "confidence": "High"}]},
    }

    def st_payload(**over):
        p = json.loads(json.dumps(base_st))
        p.update(over)
        f = tmp / "st.json"
        f.write_text(json.dumps(p), encoding="utf-8")
        return f

    # 1: missing experiment
    rc, out = run([rst, "--payload", str(st_payload(experiment_id="EXP-9999"))])
    check("trace refused: experiment missing", rc == 4, out.replace("\n", " ")[:80])

    # 2: not verified
    rc, out = run([rst, "--payload", str(st_payload(final_result="COMMAND_SUCCESS"))])
    check("trace refused: final_result not VERIFIED", rc == 4, out.replace("\n", " ")[:80])

    # 3: SUPPORTED with non-V essential
    bad_caus = {"ESSENTIAL": [{"factor": "f", "evidence": "e", "mark": "I", "confidence": "Low"}]}
    rc, out = run([rst, "--payload", str(st_payload(causality_analysis="SUPPORTED",
                                                    causality=bad_caus))])
    check("trace refused: SUPPORTED without [V] essentials", rc == 4, out.replace("\n", " ")[:90])

    # 4: <3 pass rows
    rc, out = run([rst, "--payload", str(
        st_payload(verification_table=[base_st["verification_table"][0]]))])
    check("trace refused: <3 verification rows", rc == 4, out.replace("\n", " ")[:80])

    # 5: valid dry-run (ST-9999 id reserved)
    rc, out = run([rst, "--payload", str(st_payload()), "--dry-run"])
    res = last_json(out)
    check("trace valid dry-run", rc == 0 and res.get("dry_run") is True,
          str(res.get("success_trace_id")))

    # 6: ST-0001 article
    import yaml
    st1 = WIKI / "success-traces" / "ST-0001.md"
    if st1.exists():
        fm = yaml.safe_load(st1.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        need = ("success_trace_id", "analysis_id", "experiment_id", "input_sha256",
                "environment_id", "techniques_used", "tools_used", "final_result",
                "verification_categories", "confidence", "causality_analysis")
        missing = [k for k in need if k not in fm]
        check("ST-0001 schema fields", not missing, str(missing))
        check("ST-0001 final_result VERIFIED", fm.get("final_result") == "VERIFIED_SUCCESS",
              str(fm.get("final_result")))
        check("ST-0001 causality INFERENCE", fm.get("causality_analysis") == "INFERENCE",
              str(fm.get("causality_analysis")))
    else:
        check("ST-0001 exists", False)

    # technique payloads
    base_t = {
        "name": "Test technique probe",
        "category": "static-analysis",
        "problem": "p",
        "applicable_indicators": ["x"],
        "prerequisites": {"tools": ["TR-0007"], "environment": ["host"],
                          "root_required": False, "emulator_required": False,
                          "architecture": ["any"], "android_version_min": 21,
                          "android_version_max": 99},
        "workflow": [{"observation": "o", "action": "a", "tool": "TR-0007",
                      "expected": "e", "success_indicator": "s"}],
        "decision_points": [],
        "success_indicators": ["s"],
        "verification_method": {"Structural": ["zip ok"]},
        "known_limitations": ["l"],
        "evidence": ["EXP-0001"],
        "successful_analyses": ["A-000001"],
        "failed_analyses": [],
        "confidence": 0.6,
        "promotion_state": "CANDIDATE",
        "llm_summary": "s",
        "tags": ["test"],
        "source_trace": "ST-0001",
        "version": 1,
    }

    def t_payload(**over):
        p = json.loads(json.dumps(base_t))
        p.update(over)
        f = tmp / "t.json"
        f.write_text(json.dumps(p), encoding="utf-8")
        return f

    # 7: TRUSTED with 1 evidence
    rc, out = run([rtech, "--payload", str(t_payload(promotion_state="TRUSTED",
                                                     confidence=0.95))])
    check("technique refused: TRUSTED with 1 evidence", rc == 4, out.replace("\n", " ")[:90])

    # 8: update without version bump
    rc, out = run([rtech, "--payload", str(t_payload(technique_id="T-0020", version=1))])
    check("technique refused: update without version+1", rc == 4, out.replace("\n", " ")[:90])

    # 9: workflow step missing success_indicator
    bad_step = [{"observation": "o", "action": "a", "tool": "t", "expected": "e"}]
    rc, out = run([rtech, "--payload", str(t_payload(workflow=bad_step))])
    check("technique refused: step missing indicator", rc == 4, out.replace("\n", " ")[:90])

    # 10: valid dry-run
    rc, out = run([rtech, "--payload", str(t_payload()), "--dry-run"])
    res = last_json(out)
    check("technique valid dry-run", rc == 0 and res.get("dry_run") is True,
          str(res.get("technique_id")))

    # 11: T-0020 article
    t20 = WIKI / "techniques" / "T-0020.md"
    if t20.exists():
        fm = yaml.safe_load(t20.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        need = ("technique_id", "name", "category", "problem", "applicable_indicators",
                "prerequisites", "success_indicators", "evidence", "successful_analyses",
                "failed_analyses", "confidence", "promotion_state", "version", "llm_summary")
        missing = [k for k in need if k not in fm]
        check("T-0020 schema fields", not missing, str(missing))
        check("T-0020 CANDIDATE with EXP-0001 evidence",
              fm.get("promotion_state") == "CANDIDATE" and "EXP-0001" in (fm.get("evidence") or []),
              str(fm.get("promotion_state")))
        check("T-0020 version 1", fm.get("version") == 1, str(fm.get("version")))
        body = t20.read_text(encoding="utf-8")
        check("T-0020 workflow has 4 steps", body.count("**Success Indicator:**") == 4,
              str(body.count("**Success Indicator:**")))
    else:
        check("T-0020 exists", False)

    # 12: retrieval
    rc, out = run([str(SCRIPTS / "kb_search.py"), "--text",
                   "packed APK baseline gate", "--env", "mumu-rooted-001", "--limit", "3"])
    res = last_json(out)
    top = (res.get("results") or [{}])[0]
    check("kb_search top result is T-0020 with MET prereqs",
          top.get("id") == "T-0020" and top.get("prereq_status") == "MET",
          f"{top.get('id')} {top.get('prereq_status')}")

    # 13: cross index
    idx = WIKI / "_success-trace-index.md"
    check("success-trace index has ST-0001",
          idx.exists() and "ST-0001" in idx.read_text(encoding="utf-8", errors="ignore"))

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(r[0] for r in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
