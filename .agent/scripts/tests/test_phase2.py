#!/usr/bin/env python3
"""
Phase 2 smoke test — APK fingerprint + knowledge retrieval:

  1. apk_fingerprint: JSON output has sha256, package, min_sdk, signature cert
  2. fingerprint is deterministic (same sha256 on re-run)
  3. wiki/apks article exists, YAML valid, all schema-required fields present
  4. re-running --write reuses the same analysis id (immutable records)
  5. kb_search: returns ranked results with prereq gating (stored profile or runtime fallback)
  6. kb_search: no-match query returns exit 1 with empty results (no invention)
  7. playbook catalog rows are retrievable (T-XXXX)

Run:  python .kb/scripts/tests/test_phase2.py
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
REPO = SCRIPTS.parent.parent
WIKI = REPO / "vault" / "wiki"
APK = Path("C:/Users/F A H A D/Desktop/New folder (3)/myprotectorproject.apk")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def run(args, timeout=300):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace", cwd=REPO)
    return p.returncode, (p.stdout + p.stderr).strip()


def fm_of(path):
    import yaml
    text = path.read_text(encoding="utf-8", errors="ignore")
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def main() -> int:
    if not APK.exists():
        check("test APK available", False, str(APK))
        return 1

    # 1. fingerprint JSON -----------------------------------------------------
    rc, out = run([str(SCRIPTS / "apk_fingerprint.py"), str(APK)])
    try:
        fp = json.loads(out)
        check("fingerprint sha256", len(fp.get("apk_sha256", "")) == 64, fp.get("apk_sha256", "")[:16])
        check("fingerprint package", bool(fp.get("badging", {}).get("package_name")),
              str(fp.get("badging", {}).get("package_name")))
        check("fingerprint min_sdk", bool(fp.get("badging", {}).get("min_sdk")),
              str(fp.get("badging", {}).get("min_sdk")))
        check("fingerprint signature cert", bool(fp.get("signature", {}).get("cert_sha256")),
              str(fp.get("signature", {}).get("cert_sha256"))[:16])
        check("fingerprint protection detections", len(fp.get("detections", [])) >= 1,
              f"{len(fp.get('detections', []))} detections")
        check("fingerprint zip integrity OK", fp.get("inventory", {}).get("zip_integrity") == "OK")
    except Exception as e:
        check("fingerprint JSON", False, f"{e}: {out[:200]}")
        return 1

    # 2. deterministic ----------------------------------------------------------
    rc, out2 = run([str(SCRIPTS / "apk_fingerprint.py"), str(APK)])
    fp2 = json.loads(out2)
    check("fingerprint deterministic", fp["apk_sha256"] == fp2["apk_sha256"])

    # 3. wiki article ------------------------------------------------------------
    apks = [p for p in (WIKI / "apks").glob("A-*.md")] if (WIKI / "apks").is_dir() else []
    check("apk-analysis article exists", len(apks) >= 1, f"{len(apks)} articles")
    if apks:
        fm = fm_of(apks[0])
        need = ("apk_sha256", "package_name", "version_name", "version_code", "min_sdk",
                "target_sdk", "architectures", "protection_detected", "analysis_id",
                "status", "bypass_status")
        missing = [k for k in need if k not in fm]
        check("article schema fields present", not missing, str(missing))
        check("article sha matches fingerprint", fm.get("apk_sha256") == fp["apk_sha256"])

        # 4. idempotent write ----------------------------------------------------
        rc, out3 = run([str(SCRIPTS / "apk_fingerprint.py"), str(APK), "--write"])
        try:
            res = json.loads(out3)
            check("rewrite reuses analysis id",
                  res.get("analysis_id") == fm.get("analysis_id") and res.get("reused") is True,
                  str(res.get("analysis_id")))
        except Exception as e:
            check("rewrite reuses analysis id", False, f"{e}: {out3[:200]}")

        # 5. kb_search with analysis ------------------------------------------------
        rc, out4 = run([str(SCRIPTS / "kb_search.py"), "--analysis", fm["analysis_id"],
                        "--text", "unpack VMP custom container"])
        try:
            payload = json.loads(out4)
            check("kb_search returns results", payload.get("result_count", 0) > 0,
                  f"{payload.get('result_count')} results")
            check("kb_search selects environment", bool(payload.get("environment")),
                  str(payload.get("environment")))
            kinds = {r["kind"] for r in payload.get("results", [])}
            check("kb_search returns playbook techniques",
                  any(k.startswith("T-") for r in payload.get("results", []) if r.get("id")
                      for k in [str(r["id"])]),
                  str(sorted(kinds)))
            gate_ok = all(r.get("prereq_status") in ("MET", "NOT_MET", "UNKNOWN", "N/A")
                          for r in payload.get("results", []))
            check("kb_search prereq statuses valid", gate_ok)
        except Exception as e:
            check("kb_search parse", False, f"{e}: {out4[:200]}")

    # 6. no-match query -> no invented results --------------------------------------
    rc, out5 = run([str(SCRIPTS / "kb_search.py"), "--text", "zzqqxx-nonexistent-topic-12345"])
    try:
        payload = json.loads(out5.splitlines()[-1]) if not out5.strip().startswith("{") else json.loads(out5)
        check("no-match returns empty + exit 1",
              rc == 1 and payload.get("result_count", 0) == 0,
              f"rc={rc} count={payload.get('result_count')}")
    except Exception:
        check("no-match returns empty + exit 1", rc == 1, f"rc={rc} out={out5[:120]}")

    # 7. playbook catalog retrievable -------------------------------------------------
    rc, out6 = run([str(SCRIPTS / "kb_search.py"), "--indicators", "custom container,VMP"])
    try:
        payload = json.loads(out6)
        ids = [r["id"] for r in payload.get("results", [])]
        check("playbook catalog retrievable", any(str(i).startswith("T-") for i in ids), str(ids[:6]))
    except Exception as e:
        check("playbook catalog retrievable", False, f"{e}: {out6[:200]}")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(r[0] for r in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
