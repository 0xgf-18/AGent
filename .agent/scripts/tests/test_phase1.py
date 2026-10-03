#!/usr/bin/env python3
"""
Phase 1 smoke test — verifies the initialization stack of the research loop:

  1. kb_ids: ID allocation scans the wiki and never reuses IDs
  2. tool_discover: core tools found; second run reports 'unchanged' (idempotent)
  3. tool-registry articles: valid YAML frontmatter, unique TR-XXXX ids
  4. env_probe: returns READY/DEGRADED profile with required checks
  5. volatile device state is never stored (no environment profiles, no host paths)
  6. index_builder: dry-run succeeds and respects hand-curated files
  7. graph data exists and is non-trivial

Run:  python .kb/scripts/tests/test_phase1.py
Exit: 0 = all pass, 1 = failures
"""

import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
REPO = SCRIPTS.parent.parent
WIKI = REPO / "vault" / "wiki"

results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def run(args: list[str], timeout: int = 240) -> tuple[int, str]:
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace",
                       cwd=REPO)
    return p.returncode, (p.stdout + p.stderr).strip()


def frontmatter(path: Path) -> dict:
    import yaml
    text = path.read_text(encoding="utf-8", errors="ignore")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def main() -> int:
    # 1. kb_ids -----------------------------------------------------------------
    rc, out = run([str(SCRIPTS / "kb_ids.py"), "--list"])
    try:
        ids = json.loads(out)
        ok = all(k in ids and ids[k]["next"] for k in ("A", "EXP", "ST", "T", "TR", "P", "KD"))
        check("kb_ids --list returns all prefixes", ok)
        rc, nxt = run([str(SCRIPTS / "kb_ids.py"), "--next", "TR"])
        check("kb_ids next TR is beyond registry", int(nxt.strip().split("-")[1]) > 15, nxt.strip())
    except Exception as e:
        check("kb_ids --list returns all prefixes", False, str(e))

    # 2. tool_discover idempotency ----------------------------------------------
    rc, out = run([str(SCRIPTS / "tool_discover.py")])
    try:
        run1 = json.loads(out)
        avail = [t for t in run1 if t["availability"] == "available"]
        check("tool_discover finds core tools", len(avail) >= 10, f"{len(avail)} available")
        core = {t["key"]: t for t in run1}
        check("apktool+adb+jadx present",
              all(k in core and core[k]["availability"] == "available" for k in ("adb", "apktool", "jadx")))
        rc, out2 = run([str(SCRIPTS / "tool_discover.py")])
        run2 = json.loads(out2)
        changes = {t["key"]: t["change"] for t in run2}
        bad = {k: v for k, v in changes.items() if v not in ("unchanged", "missing-new")}
        check("tool_discover idempotent (2nd run unchanged)", not bad, str(bad))
    except Exception as e:
        check("tool_discover parse", False, str(e))

    # 3. registry articles --------------------------------------------------------
    reg_dir = WIKI / "tool-registry"
    arts = sorted(reg_dir.glob("TR-*.md")) if reg_dir.is_dir() else []
    check("tool-registry articles exist", len(arts) >= 15, f"{len(arts)} articles")
    dev_arts = [a.name for a in arts if a.name.endswith("-device.md")]
    check("no device-tool articles stored (runtime-only)", not dev_arts, str(dev_arts))
    tids, yaml_ok, bad_fields = set(), True, []
    for a in arts:
        try:
            fm = frontmatter(a)
        except Exception as e:
            yaml_ok = False
            bad_fields.append(f"{a.name}: {e}")
            continue
        tid = fm.get("tool_id")
        if tid in tids:
            bad_fields.append(f"duplicate {tid}")
        tids.add(tid)
        for req in ("name", "version", "path", "category", "host_device", "input_types",
                    "output_types", "capabilities", "availability"):
            if req not in fm:
                bad_fields.append(f"{a.name}: missing {req}")
    check("registry frontmatter valid YAML", yaml_ok, "; ".join(bad_fields[:3]))
    check("registry IDs unique + schema fields", not bad_fields, "; ".join(bad_fields[:3]))

    # 4. env_probe -----------------------------------------------------------------
    rc, out = run([str(SCRIPTS / "env_probe.py")])
    try:
        prof = json.loads(out)
        check("env_probe status is READY/DEGRADED", prof.get("status") in ("READY", "DEGRADED"),
              prof.get("status"))
        names = [c["check"] for c in prof.get("checks", [])]
        need = ["ADB available", "Device responsive", "Root access", "Shell access"]
        check("env_probe mandatory checks present", all(n in names for n in need),
              str([n for n in need if n not in names]))
        # classification must be honest: rooted device -> READY with root_method,
        # non-root device -> DEGRADED with Root access FAIL (ENVIRONMENT issue, not fake)
        root_checks = [c for c in prof.get("checks", []) if c.get("check") == "Root access"]
        if prof.get("root_method"):
            ok = prof.get("status") == "READY"
            detail = f"root via {prof.get('root_method')}"
        else:
            ok = (prof.get("status") == "DEGRADED" and root_checks
                  and root_checks[0].get("status") == "FAIL")
            detail = f"non-root, status {prof.get('status')}"
        check("env_probe classifies non-root", ok, detail)
    except Exception as e:
        check("env_probe JSON", False, str(e))

    # 5. volatile device state is never stored -----------------------------------------
    env_dir = WIKI / "environments"
    envs = sorted(env_dir.glob("*.md")) if env_dir.is_dir() else []
    check("environment profiles NOT stored (runtime-only)", not envs,
          f"{len(envs)} profile files found" if envs else "absent as required")
    check("_environment-index.md removed", not (WIKI / "_environment-index.md").exists())
    host_path_hits = [a.name for a in arts
                      if re.search(r"[A-Za-z]:\\", a.read_text(encoding="utf-8", errors="ignore"))]
    check("tool articles carry no absolute host paths", not host_path_hits,
          str(host_path_hits[:3]))
    packers = sorted((WIKI / "packers").glob("*.md")) if (WIKI / "packers").is_dir() else []
    check("packers topic exists", len(packers) >= 3, f"{len(packers)} packer articles")

    # 6. index_builder ---------------------------------------------------------------
    rc, out = run([str(SCRIPTS / "index_builder.py"), "--dry-run"])
    try:
        res = json.loads(out.splitlines()[-1] if not out.strip().startswith("{") else out)
        check("index_builder dry-run ok", len(res.get("written", [])) >= 2, str(res.get("written")))
        check("hand-curated techniques index protected",
              any("techniques" in s for s in res.get("skipped", [])), str(res.get("skipped")))
    except Exception as e:
        # whole output may be the JSON object
        try:
            res = json.loads(out)
            check("index_builder dry-run ok", len(res.get("written", [])) >= 2, str(res.get("written")))
            check("hand-curated techniques index protected",
                  any("techniques" in s for s in res.get("skipped", [])), str(res.get("skipped")))
        except Exception as e2:
            check("index_builder dry-run", False, f"{e} / {e2}: {out[:200]}")

    # 7. graph data --------------------------------------------------------------------
    g = REPO / "vault" / "graph" / "graph_data.js"
    if g.exists():
        txt = g.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'"id":', txt)
        check("graph_data.js non-trivial", bool(m) and txt.count('"id"') >= 10,
              f"{txt.count(chr(34) + 'id' + chr(34))} node ids")
    else:
        check("graph_data.js exists", False)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(r[0] for r in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
