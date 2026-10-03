#!/usr/bin/env python3
"""
Phase 3 smoke test — verification gate + experiment recorder:

  1. structural PASS on a valid APK
  2. parser PASS on a valid DEX, FAIL on a corrupted DEX (adler32)
  3. content: present class PASS / absent class FAIL
  4. reproducibility: correct sha PASS / wrong sha FAIL
  5. gate: >=3 categories all PASS -> VERIFIED_SUCCESS (exit 0)
  6. gate: category FAIL -> COMMAND_SUCCESS (exit 10)
  7. gate: only 1 category -> COMMAND_SUCCESS (exit 10) - never promote
  8. record_experiment: VERIFIED with <3 categories refused (exit 4)
  9. record_experiment: FAILURE without failure_category refused (exit 4)
 10. record_experiment: valid dry-run passes (exit 0)
 11. EXP-0001 exists with schema-required frontmatter + VERIFIED_SUCCESS

Run:  python .kb/scripts/tests/test_phase3.py
"""

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
REPO = SCRIPTS.parent.parent
WIKI = REPO / "vault" / "wiki"
APK = Path("C:/Users/F A H A D/Desktop/New folder (3)/myprotectorproject.apk")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def run(args, timeout=600):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace", cwd=REPO)
    return p.returncode, (p.stdout + p.stderr).strip()


def last_json(out: str) -> dict:
    lines = [ln for ln in out.splitlines() if ln.strip().startswith("{") or ln.strip().startswith("[")]
    for ln in reversed(lines):
        try:
            return json.loads(ln)
        except Exception:
            continue
    return json.loads(out)  # multi-line json


def main() -> int:
    if not APK.exists():
        check("test APK available", False, str(APK))
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="phase3_"))
    vr = str(SCRIPTS / "verify_result.py")
    rexp = str(SCRIPTS / "record_experiment.py")

    # 1. structural
    rc, out = run([vr, "structural", "--file", str(APK), "--kind", "zip"])
    rec = last_json(out)
    check("structural PASS", rc == 0 and rec["status"] == "PASS", rec.get("details", "")[:60])

    # 2. parser good/bad
    dex = tmp / "classes.dex"
    with zipfile.ZipFile(APK) as z:
        dex.write_bytes(z.read("classes.dex"))
    rc, out = run([vr, "parser", "--dex", str(dex)])
    rec = last_json(out)
    check("parser PASS on valid dex", rc == 0 and rec["status"] == "PASS", rec.get("details", "")[:70])
    bad = tmp / "bad.dex"
    data = bytearray(dex.read_bytes())
    data[0x100] ^= 0xFF
    bad.write_bytes(bytes(data))
    rc, out = run([vr, "parser", "--dex", str(bad)])
    rec = last_json(out)
    check("parser FAIL on corrupted dex", rc == 1 and rec["status"] == "FAIL", rec.get("details", "")[:70])

    # 3. content present/absent
    rc, out = run([vr, "content", "--file", str(APK), "--class", "com.qihoo.util.VM"])
    check("content PASS on present class", rc == 0)
    rc, out = run([vr, "content", "--file", str(APK), "--class", "com.no.such.Klass"])
    check("content FAIL on absent class", rc == 1)

    # 4. reproducibility
    import hashlib
    good_sha = hashlib.sha256(APK.read_bytes()).hexdigest()
    rc, out = run([vr, "reproducibility", "--file", str(APK), "--expected-sha", good_sha])
    check("reproducibility PASS on match", rc == 0)
    rc, out = run([vr, "reproducibility", "--file", str(APK), "--expected-sha", "00" * 32])
    check("reproducibility FAIL on mismatch", rc == 1)

    # 5-7. gate verdicts
    def save(name, args):
        rc, out = run([vr] + args)
        p = tmp / name
        p.write_text(out.splitlines()[-1] if out.strip() else "{}", encoding="utf-8")
        return p

    g1 = save("g1.json", ["structural", "--file", str(APK), "--kind", "zip"])
    g2 = save("g2.json", ["parser", "--dex", str(dex)])
    g3 = save("g3.json", ["content", "--file", str(APK), "--entry", "AndroidManifest.xml"])
    g4 = save("g4.json", ["content", "--file", str(APK), "--class", "com.no.such.Klass"])
    rc, out = run([vr, "gate", str(g1), str(g2), str(g3)])
    v = last_json(out)
    check("gate 3x PASS -> VERIFIED_SUCCESS", rc == 0 and v.get("verdict") == "VERIFIED_SUCCESS",
          str(v.get("verdict")))
    rc, out = run([vr, "gate", str(g1), str(g2), str(g3), str(g4)])
    v = last_json(out)
    check("gate with FAIL -> COMMAND_SUCCESS", rc == 10 and v.get("verdict") == "COMMAND_SUCCESS",
          str(v.get("verdict")))
    rc, out = run([vr, "gate", str(g1)])
    v = last_json(out)
    check("gate 1 category -> COMMAND_SUCCESS", rc == 10 and v.get("verdict") == "COMMAND_SUCCESS",
          str(v.get("verdict")))

    # 8-10. recorder validation
    base = {
        "analysis_id": "A-000001", "technique_id": "T-0008", "toolset": ["TR-0009"],
        "environment_id": "host-runtime", "input_fingerprint": "x",
        "result": "SUCCESS", "verification_status": "VERIFIED_SUCCESS",
        "verification_categories": ["STRUCTURAL", "PARSER"],
        "steps": [{"action": "x"}], "learning": {"worked": "x"},
        "key_learning": "x", "notes": "x", "llm_summary": "x",
    }
    p_bad = tmp / "bad.json"
    p_bad.write_text(json.dumps(base), encoding="utf-8")
    rc, out = run([rexp, "--payload", str(p_bad)])
    check("recorder refuses VERIFIED with 2 categories", rc == 4, out.replace("\n", " ")[:100])

    base2 = dict(base, result="FAILURE", verification_status="COMMAND_SUCCESS",
                 failure_category=None)
    base2.pop("failure_category", None)
    p_bad2 = tmp / "bad2.json"
    p_bad2.write_text(json.dumps(base2), encoding="utf-8")
    rc, out = run([rexp, "--payload", str(p_bad2)])
    check("recorder refuses FAILURE without category", rc == 4, out.replace("\n", " ")[:100])

    base3 = dict(base, verification_categories=["STRUCTURAL", "PARSER", "CONTENT"])
    p_ok = tmp / "ok.json"
    p_ok.write_text(json.dumps(base3), encoding="utf-8")
    rc, out = run([rexp, "--payload", str(p_ok), "--dry-run"])
    res = last_json(out)
    check("recorder valid dry-run", rc == 0 and res.get("dry_run") is True, str(res.get("experiment_id")))

    # 11. EXP-0001 article
    exp = WIKI / "experiments" / "EXP-0001.md"
    if exp.exists():
        import yaml
        fm = yaml.safe_load(exp.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        need = ("experiment_id", "analysis_id", "technique_id", "toolset", "environment_id",
                "input_fingerprint", "result", "verification_status", "steps", "key_learning")
        missing = [k for k in need if k not in fm]
        check("EXP-0001 schema fields", not missing, str(missing))
        check("EXP-0001 VERIFIED_SUCCESS", fm.get("verification_status") == "VERIFIED_SUCCESS",
              str(fm.get("verification_status")))
    else:
        check("EXP-0001 exists", False)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(r[0] for r in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
