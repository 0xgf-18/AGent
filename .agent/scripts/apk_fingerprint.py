#!/usr/bin/env python3
"""
APK fingerprint — Phase 2 intake of the research loop
(see .kb/schemas/apk-analysis.md and .kb/experiment-protocol.md).

Computes: sha256, size, manifest badging (package/versions/SDK/permissions/ABI),
signature schemes + cert hash, DEX/native inventory, and protection indicators
(packer/signature heuristics from entry names + native-lib byte markers).

Usage:
    python apk_fingerprint.py <apk>                    # JSON fingerprint
    python apk_fingerprint.py <apk> --markdown         # draft article markdown
    python apk_fingerprint.py <apk> --write            # write wiki/apks/<A-ID>-<pkg>.md
    python apk_fingerprint.py <apk> --write --force    # re-allocate if hash changed

Exit codes: 0 ok, 1 bad input, 4 tooling failure.
"""

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_ids  # noqa: E402
import tool_discover  # noqa: E402

TODAY = dt.date.today().isoformat()
WIKI = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "wiki"
APKS_DIR = WIKI / "apks"

# (entry-name regex, protection, confidence, notes)
ENTRY_INDICATORS = [
    (r"libjiagu|lib360dec|assets/jiagu|libprotectclass", "360 jiagu (360加固)", "High", "360加固 loader assets/libs"),
    (r"libsecexe|libsecmain|libdexhelper|assets/bangcle", "Bangcle (梆梆加固)", "High", "Bangcle shell libraries"),
    (r"libshella|libshell-|libtup|libtxapp|assets/.+shell", "Tencent Legu (乐固)", "High", "Tencent Legu shell libs"),
    (r"libsgmain|libsgsecuritybody|libslite", "Ali Protect (阿里加固)", "High", "Ali shield libraries"),
    (r"libtencent|tavsec|libprotect", "Tencent protection", "Med", "Tencent-named protection lib"),
    (r"libdexprotector|dexprotector", "DexProtector", "High", "DexProtector marker"),
    (r"libijksafety|libmobisec|libnesec", "MobSF/other shell", "Med", "possible shell library"),
    (r"assets/.+\.(jar|dat|bin|zip|so\.dat)$", "custom container (assets)", "Med", "opaque payload asset"),
    (r"lib/.+/libapp\.so$|lib/.+/libnative\.so$", "custom native loader (possible)", "Low", "generic native entry lib"),
    (r"libbugly|crashreport", "not-a-protection", "Info", "crash reporter"),
]

# byte markers scanned inside native libs (dynstr / rodata substrings)
NATIVE_MARKERS = [
    (b"vmInterpret", "VMP / custom VM interpreter", "High"),
    (b"gVm", "VM protection marker", "Med"),
    (b"libshell", "Tencent Legu marker", "Med"),
    (b"jiagu", "360 jiagu marker", "Med"),
    (b"DexGuard", "DexGuard", "High"),
    (b"DEXCRYPT", "string-encryption marker", "Med"),
    (b"packer", "packer marker", "Low"),
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def badging(aapt: str, apk: Path) -> dict:
    out = ""
    for tool, args in ((aapt, ["dump", "badging", str(apk)]),):
        try:
            p = subprocess.run([tool] + args, capture_output=True, text=True, timeout=60,
                               encoding="utf-8", errors="replace")
            out = p.stdout or ""
        except Exception:
            out = ""
        if "package:" in out:
            break
    info = {"package_name": None, "version_name": None, "version_code": None,
            "min_sdk": None, "target_sdk": None, "launchable_activity": None,
            "permissions": [], "native_code": [], "label": None}
    if not out:
        return info
    m = re.search(r"package: name='([^']+)'(?:.*?versionCode='([^']*)')?(?:.*?versionName='([^']*)')?", out)
    if m:
        info["package_name"], info["version_code"], info["version_name"] = m.group(1), m.group(2), m.group(3)
    m = re.search(r"minSdkVersion:'(\d+)'", out) or re.search(r"(?<![A-Za-z])sdkVersion:'(\d+)'", out)
    if m:
        info["min_sdk"] = int(m.group(1))
    m = re.search(r"targetSdkVersion:'(\d+)'", out)
    if m:
        info["target_sdk"] = int(m.group(1))
    m = re.search(r"launchable-activity: name='([^']+)'", out)
    if m:
        info["launchable_activity"] = m.group(1)
    info["permissions"] = re.findall(r"uses-permission(?:-library)?: name='([^']+)'", out)
    m = re.search(r"native-code: ((?:'[^']+'\s*)+)", out)
    if m:
        info["native_code"] = sorted(set(re.findall(r"'([^']+)'", m.group(1))))
    m = re.search(r"application-label:'([^']*)'", out)
    if m:
        info["label"] = m.group(1)
    return info


def signature(apksigner: str, java: str, apk: Path) -> dict:
    sig = {"schemes": {}, "cert_sha256": None, "signer_count": 0, "verified": None}
    cmd = [apksigner, "verify", "-v", "--print-certs", str(apk)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
        out = (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        sig["error"] = str(e)
        return sig
    for m in re.finditer(r"Verified using (v\d(?:\.\d)?) scheme[^:]*:\s*(true|false)", out):
        sig["schemes"][m.group(1)] = m.group(2) == "true"
    m = re.search(r"certificate SHA-256(?: digest)?:\s*([0-9a-fA-F:]+)", out)
    if m:
        sig["cert_sha256"] = m.group(1).replace(":", "").lower()
    sig["signer_count"] = len(re.findall(r"Signer #\d+ certificate SHA-256", out))
    sig["verified"] = p.returncode == 0
    return sig


def inventory(z: zipfile.ZipFile) -> dict:
    names = z.namelist()
    dex = [n for n in names if re.fullmatch(r"classes\d*\.dex", n)]
    libs = [n for n in names if n.startswith("lib/") and n.endswith(".so")]
    abis = sorted({n.split("/")[1] for n in libs if n.count("/") >= 2})
    assets = [n for n in names if n.startswith("assets/")]
    bad = z.testzip()
    return {"dex_files": sorted(dex), "dex_count": len(dex), "native_libs": libs,
            "native_lib_count": len(libs), "abis_from_libs": abis,
            "assets": assets, "entry_count": len(names),
            "zip_integrity": "FAIL:" + str(bad) if bad else "OK",
            "has_v1_meta": any(re.match(r"META-INF/[^/]+\.(RSA|EC|DSA|SF|MF)$", n) for n in names)}


def detect_protections(z: zipfile.ZipFile, inv: dict, names: list[str]) -> list[dict]:
    detections = []
    seen = set()
    for pattern, prot, conf, notes in ENTRY_INDICATORS:
        rx = re.compile(pattern, re.I)
        hits = [n for n in names if rx.search(n)]
        if hits and prot != "not-a-protection":
            if prot not in seen:
                seen.add(prot)
                detections.append({"protection": prot, "type": "packer" if "加固" in prot or "shell" in prot.lower()
                                   or "container" in prot else "custom",
                                   "confidence": conf, "tool": "entry-name heuristic",
                                   "details": f"{len(hits)} matching entries, e.g. {hits[0]}"})
        elif hits and prot == "not-a-protection":
            if prot not in seen:
                seen.add(prot)
                detections.append({"protection": "not-a-protection", "type": "info",
                                   "confidence": "Info", "tool": "entry-name heuristic",
                                   "details": f"{hits[0]} (noise, ignore)"})
    # native byte markers (limited scan: first 2 MB of each lib)
    for lib in inv["native_libs"][:40]:
        try:
            data = z.read(lib)[:2 * 1024 * 1024]
        except Exception:
            continue
        for marker, prot, conf in NATIVE_MARKERS:
            if marker.lower() in data.lower():
                key = f"{prot}@{lib.split('/')[-1]}"
                if key not in seen:
                    seen.add(key)
                    detections.append({"protection": prot, "type": "native-marker",
                                       "confidence": conf, "tool": "byte-marker scan",
                                       "details": f"{marker.decode(errors='replace')} in {lib}"})
    if inv["dex_count"] >= 5:
        detections.append({"protection": "multi-dex (harvest candidate)", "type": "structural",
                           "confidence": "Med", "tool": "zip inventory",
                           "details": f"{inv['dex_count']} dex entries"})
    if inv["dex_count"] == 1 and inv["native_lib_count"] == 0:
        detections.append({"protection": "lightweight/no shell detected", "type": "structural",
                           "confidence": "Med", "tool": "zip inventory",
                           "details": "single dex, no native libs"})
    return detections


def fingerprint(apk: Path) -> dict:
    fp = {"apk_path": str(apk), "apk_name": apk.name, "file_size_bytes": apk.stat().st_size,
          "detection_timestamp": dt.datetime.now().isoformat(timespec="seconds"),
          "errors": []}
    fp["apk_sha256"] = sha256_of(apk)
    try:
        with zipfile.ZipFile(apk) as z:
            names = z.namelist()
            fp["inventory"] = inventory(z)
            fp["detections"] = detect_protections(z, fp["inventory"], names)
    except Exception as e:
        fp["errors"].append(f"zip: {e}")
        fp["inventory"] = {}
        fp["detections"] = []
        return fp

    cfg = json.loads((Path(__file__).resolve().parent / "tools.config.json").read_text(encoding="utf-8"))
    by_key = {t["key"]: t for t in cfg["tools"]}
    aapt2 = tool_discover.resolve_path(by_key["aapt2"]["search"])
    aapt = tool_discover.resolve_path(by_key["aapt"]["search"])
    apksigner = tool_discover.resolve_path(by_key["apksigner"]["search"])
    java = tool_discover.find_java()

    fp["badging"] = badging(aapt2 or aapt or "", apk) if (aapt2 or aapt) else {}
    if not fp["badging"].get("package_name") and aapt:
        fp["badging"] = badging(aapt, apk)
    fp["signature"] = signature(apksigner, java, apk) if apksigner else {"error": "apksigner missing"}

    abis = fp["inventory"].get("abis_from_libs") or fp["badging"].get("native_code") or []
    fp["architectures"] = abis
    prot = sorted({d["protection"] for d in fp["detections"] if d["type"] != "info"})
    fp["protection_detected"] = prot
    return fp


# ---------------------------------------------------------------- article ---
def existing_analysis(sha: str) -> dict | None:
    if not APKS_DIR.is_dir():
        return None
    for md in APKS_DIR.glob("*.md"):
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if f"apk_sha256: {sha}" in text:
            fm = {}
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            fm[k.strip()] = v.strip().strip('"').strip("'")
            return {"file": md, "analysis_id": fm.get("analysis_id"),
                    "status": fm.get("status", "in-progress"),
                    "bypass_status": fm.get("bypass_status", "not-attempted")}
    return None


def to_markdown(fp: dict, analysis_id: str, status: str, bypass: str) -> str:
    inv = fp.get("inventory", {})
    bad = fp.get("badging", {})
    sig = fp.get("signature", {})
    det_rows = "\n".join(
        f"| {d['type']} | {'Yes' if d['type'] != 'info' else 'n/a'} | {d['tool']} | {d['confidence']} | {d['details']} |"
        for d in fp.get("detections", [])) or "| (none detected) | No | — | — | run deeper static analysis |"
    schemes = ", ".join(f"{k}={v}" for k, v in sig.get("schemes", {}).items()) or "unknown"
    dex_list = ", ".join(inv.get("dex_files", [])) or "—"
    libs = ", ".join(inv.get("native_libs", [])[:12]) or "—"
    return f"""---
type: apk-analysis
topic: wiki/apks/_index
source: {fp['apk_sha256']}
tags: [apk, fingerprint, {fp.get('protection_detected', ['unknown'])[0] if fp.get('protection_detected') else 'unknown'}]
complexity: advanced
completeness: partial
last_verified: {TODAY}
tool_versions: [apktool 2.11.1, aapt2 35.0.0, apksigner 35.0.0]
apk_sha256: {fp['apk_sha256']}
package_name: {bad.get('package_name') or 'unknown'}
version_name: {bad.get('version_name') or 'unknown'}
version_code: {bad.get('version_code') or 'unknown'}
min_sdk: {bad.get('min_sdk') or 'unknown'}
target_sdk: {bad.get('target_sdk') or 'unknown'}
architectures: {json.dumps(fp.get('architectures', []))}
protection_detected: {json.dumps(fp.get('protection_detected', []))}
analysis_id: {analysis_id}
status: {status}
bypass_status: {bypass}
llm_summary: "{bad.get('package_name') or fp['apk_name']} ({bad.get('version_name') or '?'}): {', '.join(fp.get('protection_detected', [])) or 'no protection detected by fingerprint heuristics'} — {inv.get('dex_count', '?')} dex, {inv.get('native_lib_count', '?')} native libs, cert {str(sig.get('cert_sha256'))[:16]}..."
---

# {bad.get('package_name') or fp['apk_name']} — APK Analysis

## This Article Answers
- "What protections does {bad.get('package_name') or fp['apk_name']} use?"
- "How can this APK be unpacked/analyzed?"
- "What techniques were successful against {', '.join(fp.get('protection_detected', []))[:60] or 'this APK'}?"

## Key Takeaways
- [PROTECTION] {', '.join(fp.get('protection_detected', [])) or 'none detected by heuristics (deeper static analysis required)'}
- [PACKER] {[d['protection'] for d in fp.get('detections', []) if d['type'] == 'packer'] or 'not identified'}
- [OBSERVATION] {inv.get('dex_count', '?')} dex, {inv.get('native_lib_count', '?')} native libs, zip integrity {inv.get('zip_integrity', '?')}
- [RESULT] fingerprint intake only — analysis {status}

## APK Fingerprint
| Property | Value |
|---|---|
| SHA256 | `{fp['apk_sha256']}` |
| Package | `{bad.get('package_name')}` |
| Version | {bad.get('version_name')} (code: {bad.get('version_code')}) |
| Min SDK | {bad.get('min_sdk')} |
| Target SDK | {bad.get('target_sdk')} |
| Architectures | `{', '.join(fp.get('architectures', [])) or 'unknown'}` |
| File Size | `{round(fp['file_size_bytes'] / 1048576, 2)} MB` |
| DEX Count | {inv.get('dex_count', '?')} |
| Native Libraries | {inv.get('native_lib_count', '?')} |
| Entry count | {inv.get('entry_count', '?')} |
| Zip integrity | {inv.get('zip_integrity', '?')} |
| Launch activity | `{bad.get('launchable_activity')}` |
| Permissions | {len(bad.get('permissions', []))} |
| Signature schemes | {schemes} |
| Cert SHA-256 | `{sig.get('cert_sha256')}` |
| Source APK | `{fp['apk_name']}` (host path runtime-only, never stored) |

## Protection Detection Results
| Protection Type | Detected | Tool | Confidence | Details |
|---|---|---|---|---|
{det_rows}

## Static Analysis Findings
### DEX Analysis
- DEX entries: `{dex_list}`
- Class counts / obfuscation: _not yet analyzed (Phase 2 static pass pending)_

### Native Library Analysis
| Library | Architecture | Exports | Suspicious Functions | Protection Signs |
|---|---|---|---|---|
{chr(10).join(f"| `{l}` | {l.split('/')[1] if l.count('/') > 1 else '?'} | — | — | scan pending |" for l in inv.get('native_libs', [])[:10]) or '| — | — | — | — | none |'}

### Resource Analysis
- Assets: {len(inv.get('assets', []))} files — `{', '.join(inv.get('assets', [])[:8]) or 'none'}`
- Suspicious files: {[d['details'] for d in fp.get('detections', []) if 'assets' in d['details']] or 'none flagged'}

## Dynamic Analysis Observations
### Runtime Behavior (MuMu)
- _not yet run_ (dynamic phase pending)

### Frida/Objection Hooks Attempted
| Hook Target | Result | Notes |
|---|---|---|
| — | — | no hooks yet |

## Experiments Conducted
| Experiment ID | Technique | Tools | Environment | Result | Verification |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Successful Workflow (if any)
> References: [[wiki/techniques/apk-unpacking-playbook]] (intake checklist)

## Failed Attempts
| Attempt | Technique | Failure Reason | Evidence |
|---|---|---|---|
| — | — | — | — |

## Extracted Artifacts
| Artifact ID | Type | Source Experiment | Hash | Location | Verified |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## What This Article Does NOT Cover
- Runtime behavior, dynamic instrumentation, and bypass results — filled in as experiments run
- Verbatim unpacking commands — recorded in experiment records, not here

## Open Questions / Unverified Claims
- Protection detections are heuristics ([AI Synthesis]) until confirmed by a tool-verified experiment `[V]`

## Related
- [[wiki/techniques/apk-unpacking-playbook]] — intake checklist
- [[wiki/packers/_index]] — packers (packer name -> verified unpacking method)
- environment: host-runtime (runtime-only, never stored)
- [[wiki/tool-registry/_index]] — tool registry
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Fingerprint an APK (Phase 2 intake).")
    ap.add_argument("apk", help="path to the APK")
    ap.add_argument("--write", action="store_true", help="write wiki/apks/<A-ID>-<pkg>.md")
    ap.add_argument("--markdown", action="store_true", help="print draft article markdown")
    ap.add_argument("--analysis-id", help="reuse a specific A-XXXXXX id")
    args = ap.parse_args()

    apk = Path(args.apk)
    if not apk.is_file() or apk.suffix.lower() not in (".apk", ".zip", ".apks", ".aab"):
        print(json.dumps({"error": f"not an APK file: {apk}"}))
        return 1

    try:
        fp = fingerprint(apk)
    except Exception as e:
        print(json.dumps({"error": f"fingerprint failed: {e}"}))
        return 4

    existing = existing_analysis(fp["apk_sha256"])
    if existing:
        analysis_id = args.analysis_id or existing["analysis_id"]
        status, bypass = existing["status"], existing["bypass_status"]
        fp["existing_analysis"] = str(existing["file"])
    else:
        analysis_id = args.analysis_id or kb_ids.fmt("A", kb_ids.scan(WIKI).get("A", 0) + 1)
        status, bypass = "in-progress", "not-attempted"

    fp["analysis_id"] = analysis_id

    if args.markdown or args.write:
        md = to_markdown(fp, analysis_id, status, bypass)
        if args.markdown:
            print(md)
        if args.write:
            APKS_DIR.mkdir(parents=True, exist_ok=True)
            pkg = re.sub(r"[^A-Za-z0-9._-]", "-", fp.get("badging", {}).get("package_name") or apk.stem)
            path = APKS_DIR / f"{analysis_id}-{pkg}.md"
            path.write_text(md, encoding="utf-8")
            print(json.dumps({"written": str(path), "analysis_id": analysis_id,
                              "reused": bool(existing)}, indent=2))
        return 0

    out = {k: v for k, v in fp.items() if k != "inventory"}
    out["inventory"] = {k: (v if not isinstance(v, list) else v[:20])
                        for k, v in fp.get("inventory", {}).items()}
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
