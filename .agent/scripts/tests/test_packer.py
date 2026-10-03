#!/usr/bin/env python3
"""
Packer restructure smoke test — the packer -> unpacking-method storage layer:

  1. packers topic: >=3 articles, valid packer frontmatter
  2. unpacking honesty: status=unpacked requires verified evidence OR documented_in
  3. record_packer.py: refuses unverified 'unpacked' (rc 4), accepts valid payloads
  4. kb_search: returns kind=packer results with valid prereq statuses
  5. graph: packer nodes present, no environments (volatile) nodes, no host paths
  6. generated indexes: _packer-index.md present and populated

Run:  python .kb/scripts/tests/test_packer.py
Exit: 0 = all pass, 1 = failures
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
REPO = SCRIPTS.parent.parent
WIKI = REPO / "vault" / "wiki"

results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def run(args: list[str], timeout: int = 120) -> tuple[int, str]:
    import os
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace",
                       cwd=REPO, env=env)
    return p.returncode, (p.stdout + p.stderr).strip()


def frontmatter(path: Path) -> dict:
    import yaml
    text = path.read_text(encoding="utf-8", errors="ignore")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def base_payload(**over) -> dict:
    p = {
        "packer_id": "test-packer",
        "name": "Test Packer",
        "protection_class": "packer",
        "aliases": [],
        "indicators": ["stub dex marker"],
        "unpacking_status": "attempted",
        "confidence": 0.5,
        "evidence": [],
        "technique_ids": [],
        "tools": ["TR-0002"],
        "documented_in": "",
        "unpacking_method": [{"name": "Triage", "action": "entry inventory",
                              "tool": "apk_fingerprint.py"}],
        "verification": [{"category": "PARSER", "check": "dex header",
                          "pass_condition": "valid"}],
        "failure_conditions": [],
        "decision_points": [],
        "tags": ["packer"],
        "llm_summary": "test packer for schema checks",
    }
    p.update(over)
    return p


def write_payload(p: dict) -> str:
    f = Path(tempfile.gettempdir()) / "packer_payload_test.json"
    f.write_text(json.dumps(p), encoding="utf-8")
    return str(f)


def main() -> int:
    # 1. packers topic ------------------------------------------------------------
    pdir = WIKI / "packers"
    arts = sorted(pdir.glob("*.md")) if pdir.is_dir() else []
    arts = [a for a in arts if not a.name.startswith("_")]
    check("packers topic has >=3 articles", len(arts) >= 3, f"{len(arts)} articles")

    packers = {}
    for a in arts:
        try:
            fm = frontmatter(a)
        except Exception as e:
            check(f"packer YAML: {a.name}", False, str(e))
            continue
        packers[a.stem] = fm
        missing = [k for k in ("type", "packer_id", "name", "protection_class",
                               "indicators", "unpacking_status", "confidence",
                               "evidence", "technique_ids", "tools",
                               "documented_in", "version", "llm_summary")
                   if k not in fm]
        check(f"packer frontmatter fields: {a.stem}", not missing, str(missing))
        check(f"packer type: {a.stem}", fm.get("type") == "packer", str(fm.get("type")))
        body = a.read_text(encoding="utf-8", errors="ignore")
        check(f"packer body has Unpacking Method: {a.stem}",
              "## Unpacking Method" in body and "## Identification" in body)

    # 2. unpacking honesty --------------------------------------------------------
    import yaml
    for stem, fm in packers.items():
        status = fm.get("unpacking_status")
        check(f"status valid: {stem}", status in
              ("not_attempted", "attempted", "unpacked", "blocked"), str(status))
        if status == "unpacked":
            verified = []
            for eid in (fm.get("evidence") or []):
                ep = WIKI / "experiments" / f"{eid}.md"
                if ep.exists():
                    efm = frontmatter(ep)
                    if efm.get("verification_status") == "VERIFIED_SUCCESS":
                        verified.append(eid)
            documented = str(fm.get("documented_in") or "").strip()
            check(f"unpacked is backed by evidence: {stem}",
                  bool(verified) or bool(documented),
                  f"verified={verified} documented_in={documented!r}")

    # 3. record_packer.py ---------------------------------------------------------
    rc, out = run([str(SCRIPTS / "record_packer.py"), "--payload",
                   write_payload(base_payload(packer_id="jiagu-lite",
                                              unpacking_status="unpacked"))])
    check("record_packer refuses unverified unpacked (rc 4)", rc == 4, out[:200])

    rc, out = run([str(SCRIPTS / "record_packer.py"), "--payload",
                   write_payload(base_payload(packer_id="jiagu-lite",
                                              unpacking_method=[])), "--dry-run"])
    check("record_packer refuses empty unpacking_method (rc 4)", rc == 4, out[:200])

    rc, out = run([str(SCRIPTS / "record_packer.py"), "--payload",
                   write_payload(base_payload(packer_id="jiagu-lite")), "--dry-run"])
    check("record_packer accepts valid payload (dry-run rc 0)", rc == 0, out[:200])

    # update path: existing packer needs version bump
    rc, out = run([str(SCRIPTS / "record_packer.py"), "--payload",
                   write_payload(base_payload(packer_id="360-jiagu", version=1)),
                   "--dry-run"])
    check("record_packer enforces version bump on update (rc 4)", rc == 4, out[:200])

    # 4. kb_search packer kind ----------------------------------------------------
    rc, out = run([str(SCRIPTS / "kb_search.py"), "--text", "unpack 360 jiagu", "--limit", "8"])
    try:
        payload = json.loads(out)
        kinds = [r.get("kind") for r in payload.get("results", [])]
        check("kb_search returns kind=packer results", "packer" in kinds, str(kinds))
        top = payload["results"][0] if payload.get("results") else {}
        check("top result is a packer article",
              top.get("kind") == "packer", f"{top.get('id')} {top.get('kind')}")
        valid_status = {"MET", "NOT_MET", "UNKNOWN", "N/A"}
        bad = [r for r in payload["results"] if r.get("prereq_status") not in valid_status]
        check("prereq statuses valid", not bad, str(bad[:2]))
        env = payload.get("environment") or {}
        check("environment context present (runtime fallback)",
              bool(env) and env.get("gate_mode") in ("tool-registry-fallback", "stored-profile"),
              str(env.get("gate_mode")))
    except Exception as e:
        check("kb_search packer parse", False, f"{e}: {out[:200]}")

    # 5. graph --------------------------------------------------------------------
    g = REPO / "vault" / "graph" / "graph_data.js"
    txt = g.read_text(encoding="utf-8", errors="ignore") if g.exists() else ""
    check("graph has packer nodes", '"wiki/packers/' in txt)
    check("graph has no environments nodes", '"id": "wiki/environments' not in txt)
    check("graph carries no absolute host paths", "C:\\\\Users" not in txt,
          "host paths scrubbed")
    check("graph has no device-tool nodes",
          '"id": "wiki/tool-registry/tr-0016' not in txt
          and '"id": "wiki/tool-registry/tr-0021' not in txt)

    # 6. generated indexes --------------------------------------------------------
    px = WIKI / "_packer-index.md"
    check("_packer-index.md generated", px.exists())
    if px.exists():
        t = px.read_text(encoding="utf-8", errors="ignore")
        check("_packer-index lists 3 packers",
              all(s in t for s in ("360-jiagu", "xuandun", "virex")), t[:200])
        check("_packer-index carries generator marker",
              "generated by index_builder.py" in t)
    check("_environment-index.md absent", not (WIKI / "_environment-index.md").exists())

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(r[0] for r in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
