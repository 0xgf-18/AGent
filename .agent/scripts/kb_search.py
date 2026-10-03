#!/usr/bin/env python3
"""
Knowledge search / strategy-planner support — Phase 2 of the research loop
(see .kb/experiment-protocol.md section 2).

Retrieves reusable knowledge BEFORE experimenting:
  - packer articles (packer name -> verified unpacking method, first stop)
  - technique articles (structured prerequisites -> gated against an environment)
  - playbook catalog rows (unstructured -> prereq status UNKNOWN)
  - pattern articles (applicable_indicators)
  - success traces (verified workflows)
  - prior apk-analyses (same package/sha => prior art)

Prerequisite gate:
  - with a stored environment profile: root/emulator/arch/android/tool availability
    -> MET | NOT_MET (+missing) | UNKNOWN
  - runtime-only fallback (no stored profiles - volatile device state is never
    persisted): tools are gated against tool-registry availability, device-bound
    requirements (root/emulator/arch) -> UNKNOWN with a run-env-probe note

Usage:
    python kb_search.py --indicators "vmInterpret,libjiagu,multi-dex"
    python kb_search.py --analysis A-000001            # pull indicators from an APK article
    python kb_search.py --text "unpack 360 jiagu on rooted emulator"
    python kb_search.py --text "jiagu" --env physical-noroot-001 --markdown

Exit: 0 results, 1 no results, 4 error.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

WIKI = Path(__file__).resolve().parent.parent.parent / "vault" / "articles"


def parse_fm(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    if HAS_YAML:
        try:
            return yaml.safe_load(parts[1]) or {}
        except Exception:
            pass
    fm = {}
    for line in parts[1].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def load_articles() -> list[dict]:
    out = []
    for md in sorted(WIKI.rglob("*.md")):
        if md.name.startswith("_"):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        fm = parse_fm(text)
        if not fm:
            continue
        out.append({"file": md, "fm": fm, "rel": md.relative_to(WIKI).with_suffix("").as_posix(),
                    "text": text})
    return out


def playbook_catalog(articles: list[dict]) -> list[dict]:
    """Rows like '| T-0001 | Name | category | phase | proven-on |' from technique wiki files."""
    known = {a["fm"].get("technique_id") for a in articles if a["fm"].get("type") == "technique"}
    rows = []
    rx = re.compile(r"^\|\s*(T-\d{4})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.M)
    for a in articles:
        if not a["rel"].startswith("techniques/"):
            continue
        for m in rx.finditer(a["text"]):
            tid, name, cat = m.group(1), m.group(2).strip(), m.group(3).strip()
            if tid in known or name.lower() in ("technique", "name"):
                continue
            rows.append({"id": tid, "name": name, "category": cat, "file": a["rel"],
                         "kind": "playbook-catalog"})
    seen, uniq = set(), []
    for r in rows:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    return uniq


def tokens(s: str) -> set:
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) > 2}


def score_candidate(query_tokens: set, indicators: list[str], hay: str, name: str) -> tuple[float, list]:
    hay_cf = (hay or "").lower()
    name_cf = (name or "").lower()
    matched = []
    score = 0.0
    for ind in indicators:
        ind_cf = ind.strip().lower()
        if ind_cf and ind_cf in hay_cf:
            score += 3.0
            matched.append(f"indicator:{ind.strip()}")
    q = query_tokens & tokens(name_cf)
    if q:
        score += 2.0 * len(q)
        matched += [f"name:{t}" for t in sorted(q)]
    q2 = (query_tokens & tokens(hay_cf)) - q
    if q2:
        score += 1.0 * min(len(q2), 5)
        matched += [f"text:{t}" for t in sorted(q2)[:5]]
    return score, matched


def pick_environment(articles: list[dict], wanted: str | None) -> dict | None:
    envs = [a for a in articles if a["fm"].get("type") == "environment-profile"]
    if not envs:
        return None
    if wanted:
        for e in envs:
            if e["fm"].get("environment_id") == wanted:
                return e
        return None
    ready = [e for e in envs if e["fm"].get("status") == "READY"]
    pool = ready or envs
    pool.sort(key=lambda e: str(e["fm"].get("detection_timestamp", "")), reverse=True)
    return pool[0]


def available_tools(articles: list[dict]) -> set:
    """Tool ids whose registry entry says availability=available (host runtime)."""
    out = set()
    for a in articles:
        fm = a["fm"]
        if fm.get("type") == "tool-registry" and fm.get("tool_id"):
            if str(fm.get("availability", "")).lower() in ("available", "ok", "installed"):
                out.add(str(fm["tool_id"]))
    return out


def prereq_tool_ids(prereqs: dict) -> list:
    ids = []
    for key in ("tools", "host_tools", "device_tools"):
        v = prereqs.get(key)
        if isinstance(v, list):
            ids += [str(x) for x in v]
    return ids


def gate_prereqs(prereqs: dict, env: dict | None, available: set) -> tuple[str, list]:
    if not isinstance(prereqs, dict) or not prereqs:
        return "UNKNOWN", []
    if not env:
        # runtime-only fallback: gate against tool-registry availability;
        # device-bound requirements need a live env-probe -> UNKNOWN
        missing = [f"tool:{t}" for t in prereq_tool_ids(prereqs) if t not in available]
        if missing:
            return "NOT_MET", missing
        notes = []
        if prereqs.get("root_required"):
            notes.append("root: run env-probe (device-bound, not stored)")
        if prereqs.get("emulator_required"):
            notes.append("emulator: run env-probe (device-bound, not stored)")
        arch = prereqs.get("architecture")
        if arch and isinstance(arch, list) and "any" not in [str(x).lower() for x in arch]:
            notes.append("arch: run env-probe (device-bound, not stored)")
        if notes:
            return "UNKNOWN", notes
        return "MET", []
    ef = env["fm"]
    missing = []
    if prereqs.get("root_required") and str(ef.get("root_available")).lower() != "true":
        missing.append("root")
    if prereqs.get("emulator_required") and ef.get("device_type") != "emulator":
        missing.append("emulator")
    arch = prereqs.get("architecture")
    if arch and isinstance(arch, list) and "any" not in [str(x).lower() for x in arch] \
            and ef.get("architecture") not in arch:
        missing.append(f"arch:{ef.get('architecture')} not in {arch}")
    try:
        api = int(ef.get("api_level") or 0)
        lo = int(prereqs.get("android_version_min") or 0)
        hi = int(prereqs.get("android_version_max") or 999)
        if api and lo and api < lo:
            missing.append(f"android {api} < min {lo}")
        if api and hi and api > hi:
            missing.append(f"android {api} > max {hi}")
    except (TypeError, ValueError):
        pass
    env_tools = set()
    for key in ("host_tools", "device_tools"):
        v = ef.get(key)
        if isinstance(v, list):
            env_tools |= set(str(x) for x in v)
    for t in (prereqs.get("tools") or []) + (prereqs.get("host_tools") or []) + (prereqs.get("device_tools") or []):
        if str(t) not in env_tools:
            missing.append(f"tool:{t}")
    return ("NOT_MET" if missing else "MET"), missing


def main() -> int:
    ap = argparse.ArgumentParser(description="Search KB knowledge for the strategy planner.")
    ap.add_argument("--indicators", help="comma-separated fingerprint indicators")
    ap.add_argument("--text", default="", help="free-text goal description")
    ap.add_argument("--tags", help="comma-separated tags")
    ap.add_argument("--analysis", help="A-XXXXXX: load indicators from that apk-analysis article")
    ap.add_argument("--env", help="environment_id for the prerequisite gate (default: latest READY)")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    try:
        articles = load_articles()
    except Exception as e:
        print(json.dumps({"error": f"kb load failed: {e}"}))
        return 4

    indicators, priors = [], []
    if args.analysis:
        hit = next((a for a in articles
                    if a["fm"].get("analysis_id") == args.analysis
                    or a["rel"].endswith(args.analysis)), None)
        if not hit:
            print(json.dumps({"error": f"analysis not found: {args.analysis}"}))
            return 1
        indicators += [str(x) for x in (hit["fm"].get("protection_detected") or [])]
        indicators += ["prior-art-" + str(hit["fm"].get("package_name"))]
        priors.append({"id": args.analysis, "package": hit["fm"].get("package_name"),
                       "file": hit["rel"], "why": "same analysis being planned"})
    if args.indicators:
        indicators += [x.strip() for x in args.indicators.split(",") if x.strip()]
    if args.tags:
        indicators += [x.strip() for x in args.tags.split(",") if x.strip()]

    # prior art: other apk-analyses with same package
    pkg = next((a["fm"].get("package_name") for a in articles
                if a["fm"].get("analysis_id") == args.analysis), None)
    if pkg:
        for a in articles:
            if a["fm"].get("type") == "apk-analysis" and a["fm"].get("package_name") == pkg \
                    and a["fm"].get("analysis_id") != args.analysis:
                priors.append({"id": a["fm"].get("analysis_id"), "package": pkg,
                               "file": a["rel"], "why": "prior analysis of same package"})

    env = pick_environment(articles, args.env)
    avail = available_tools(articles)
    query_tokens = tokens(args.text) | tokens(" ".join(indicators))

    results = []
    for a in articles:
        t = a["fm"].get("type")
        if t == "packer":
            hay = " ".join(str(a["fm"].get(k, "")) for k in
                           ("name", "aliases", "indicators", "protection_class",
                            "tags", "unpacking_status", "llm_summary"))
            sc, matched = score_candidate(query_tokens, indicators, hay, a["fm"].get("name", ""))
            if sc <= 0:
                continue
            status, missing = gate_prereqs({"tools": a["fm"].get("tools") or []}, env, avail)
            results.append({
                "id": a["fm"].get("packer_id"), "name": a["fm"].get("name"),
                "kind": "packer", "file": a["rel"], "score": round(sc, 2),
                "matched": matched[:8], "prereq_status": status, "missing": missing,
                "unpacking_status": a["fm"].get("unpacking_status"),
                "confidence": a["fm"].get("confidence")})
        elif t == "technique":
            hay = " ".join(str(a["fm"].get(k, "")) for k in
                           ("name", "problem", "applicable_indicators", "tags", "llm_summary"))
            sc, matched = score_candidate(query_tokens, indicators, hay, a["fm"].get("name", ""))
            if sc <= 0:
                continue
            status, missing = gate_prereqs(a["fm"].get("prerequisites") or {}, env, avail)
            results.append({
                "id": a["fm"].get("technique_id"), "name": a["fm"].get("name"),
                "kind": "technique", "file": a["rel"], "score": round(sc, 2),
                "matched": matched[:8], "prereq_status": status, "missing": missing,
                "confidence": a["fm"].get("confidence"), "promotion_state": a["fm"].get("promotion_state")})
        elif t == "pattern":
            hay = " ".join([str(a["fm"].get("name", "")), str(a["fm"].get("applicable_indicators", "")),
                            str(a["fm"].get("llm_summary", "")), str(a["fm"].get("tags", ""))])
            sc, matched = score_candidate(query_tokens, indicators, hay, a["fm"].get("name", ""))
            if sc > 0:
                results.append({"id": a["fm"].get("pattern_id"), "name": a["fm"].get("name"),
                                "kind": "pattern", "file": a["rel"], "score": round(sc, 2),
                                "matched": matched[:8], "prereq_status": "N/A", "missing": []})
        elif t == "success-trace":
            hay = " ".join(str(a["fm"].get(k, "")) for k in ("goal", "tags", "llm_summary"))
            sc, matched = score_candidate(query_tokens, indicators, hay, a["fm"].get("name", ""))
            if sc > 0:
                results.append({"id": a["fm"].get("success_trace_id"),
                                "name": a["fm"].get("goal") or str(a["fm"].get("llm_summary", ""))[:70],
                                "kind": "success-trace", "file": a["rel"], "score": round(sc, 2),
                                "matched": matched[:8], "prereq_status": "N/A", "missing": []})
        elif t == "apk-analysis" and args.analysis and a["fm"].get("analysis_id") != args.analysis:
            hay = " ".join([str(a["fm"].get("package_name", "")),
                            str(a["fm"].get("protection_detected", "")),
                            str(a["fm"].get("llm_summary", ""))])
            sc, matched = score_candidate(query_tokens, indicators, hay, a["fm"].get("name", ""))
            if sc > 0:
                results.append({"id": a["fm"].get("analysis_id"), "name": a["fm"].get("package_name"),
                                "kind": "prior-analysis", "file": a["rel"], "score": round(sc, 2),
                                "matched": matched[:8], "prereq_status": "N/A", "missing": []})

    # playbook catalog entries (no structured prerequisites -> UNKNOWN)
    if query_tokens or indicators:
        for r in playbook_catalog(articles):
            hay = f"{r['name']} {r['category']}"
            sc, matched = score_candidate(query_tokens, indicators, hay, r["name"])
            if sc > 0:
                results.append({"id": r["id"], "name": r["name"], "kind": r["kind"],
                                "file": r["file"], "score": round(sc, 2), "matched": matched[:8],
                                "prereq_status": "UNKNOWN",
                                "missing": ["playbook entry - prerequisites in playbook Phase sections"]})

    results.sort(key=lambda r: (-r["score"], str(r["id"])))
    results = results[:args.limit]

    if env:
        environment = {"id": env["fm"].get("environment_id"), "status": env["fm"].get("status"),
                       "root": env["fm"].get("root_available"), "arch": env["fm"].get("architecture"),
                       "api": env["fm"].get("api_level"), "gate_mode": "stored-profile"}
    else:
        # volatile device state is never persisted -> runtime-only context
        environment = {"id": "host-runtime", "status": "RUNTIME_ONLY",
                       "root": "unknown", "arch": "unknown", "api": None,
                       "gate_mode": "tool-registry-fallback",
                       "note": "no stored environment profiles; run env_probe.py "
                               "--health for live device state; device-bound "
                               "prerequisites gate as UNKNOWN"}
    payload = {
        "query": {"indicators": indicators, "text": args.text},
        "environment": environment,
        "prior_art": priors,
        "result_count": len(results),
        "results": results,
        "planner_hint": ("No knowledge matched - treat as novel APK; start with T-0001 triage playbook."
                         if not results else
                         "Order experiments by score; skip NOT_MET until prerequisites are met; "
                         "record every attempt as EXP-XXXX."),
    }

    if args.markdown:
        print(f"Environment: {payload['environment']}")
        print("| Score | ID | Name | Kind | Prereqs | Missing | File |")
        print("|---|---|---|---|---|---|---|")
        for r in results:
            print(f"| {r['score']} | {r['id']} | {r['name'][:50]} | {r['kind']} "
                  f"| {r['prereq_status']} | {'; '.join(r['missing'])[:60]} | {r['file']} |")
        return 0 if results else 1

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
