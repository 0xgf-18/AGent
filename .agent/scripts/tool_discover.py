#!/usr/bin/env python3
"""
Tool discovery — builds/updates the Tool Registry
(see .kb/schemas/tool-registry.md).

Probes PATH, known SDK/tool locations (tools.config.json) and Python modules,
extracts versions, compares against existing wiki/tool-registry/*.md articles,
and assigns sequential TR-XXXX IDs via kb_ids (IDs are never reused).

Usage:
    python tool_discover.py                       # JSON list of tool records
    python tool_discover.py --markdown             # summary table
    python tool_discover.py --write                # create/update registry articles
    python tool_discover.py --serial 127.0.0.1:16416   # also probe device tools
    python tool_discover.py --serial SER --write   # register host + device tools

Exit codes: 0 = at least one core tool available, 5 = nothing usable.
"""

import argparse
import datetime as dt
import glob as globmod
import importlib.metadata as imd
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import kb_ids

HOST = os.name == "nt"
TODAY = dt.date.today().isoformat()

CONFIG_PATH = Path(__file__).resolve().parent / "tools.config.json"
REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / "vault" / "articles" / "tool-registry"
REPO = Path(__file__).resolve().parent.parent.parent

# Schema categories (.kb/schemas/tool-registry.md)
TOOL_META = {
    "adb": dict(
        category="dynamic-observation", subcategory="device-bridge", host_device="both",
        input_types=["apk", "directory", "process", "log"],
        output_types=["dex", "json", "text", "log", "binary"],
        capabilities=["install/uninstall APKs", "launch activities & dump logcat",
                      "shell command execution as shell/root", "pull/push files (fs inspection)",
                      "port forwarding for dynamic instrumentation"],
        install_method="download", install_command="sdkmanager platform-tools",
        verification="adb version", common_flags="-s <serial> shell logcat install -r pull push forward",
        examples=[("Install an APK", "adb -s <serial> install -r app.apk"),
                  ("Dump logcat", "adb -s <serial> logcat -d > logcat.txt")],
        deps=[]),
    "apktool": dict(
        category="apk-inspection", subcategory="decompile-rebuild", host_device="host",
        input_types=["apk"], output_types=["smali", "xml", "directory"],
        capabilities=["APK decode to smali + resources", "rebuild APK from smali",
                      "smali/baksmali of any dex"],
        install_method="download", install_command="java -jar apktool.jar",
        verification="java -jar apktool.jar --version", common_flags="d -f -o out b -o out.apk if",
        examples=[("Decode", "java -jar apktool.jar d -f app.apk -o app_edit"),
                  ("Rebuild", "java -jar apktool.jar b app_edit -o rebuild.apk")],
        deps=["java"]),
    "jadx": dict(
        category="dex-analysis", subcategory="decompiler", host_device="host",
        input_types=["apk", "dex", "jar", "smali"],
        output_types=["decompiled-java", "resource", "report"],
        capabilities=["DEX/APK to readable Java", "resource extraction",
                      "cross-references and search"],
        install_method="download", install_command="jadx (release zip)",
        verification="jadx --version", common_flags="-d out --no-res -j 4",
        examples=[("Decompile APK", "jadx -d out app.apk"),
                  ("Single class", "jadx --single-class com.foo.Bar app.apk")],
        deps=[]),
    "java": dict(
        category="other", subcategory="runtime", host_device="host",
        input_types=["jar", "apk"], output_types=["report"],
        capabilities=["runs JVM tooling (apktool, apksigner, baksmali)"],
        install_method="download", install_command="Temurin JDK 17",
        verification="java -version", common_flags="-Xmx2g",
        examples=[("Version", "java -version")], deps=[]),
    "aapt2": dict(
        category="resource-analysis", subcategory="manifest", host_device="host",
        input_types=["apk"], output_types=["xml", "text"],
        capabilities=["dump badging (package, version, permissions, launchable activity)",
                      "compile/link resources"],
        install_method="download", install_command="sdkmanager build-tools;35.0.0",
        verification="aapt2 version", common_flags="dump badging",
        examples=[("Badging", "aapt2 dump badging app.apk")], deps=[]),
    "aapt": dict(
        category="resource-analysis", subcategory="manifest-legacy", host_device="host",
        input_types=["apk"], output_types=["xml", "text"],
        capabilities=["dump badging/xmltree of APK manifest and resources"],
        install_method="download", install_command="sdkmanager build-tools;35.0.0",
        verification="aapt v", common_flags="dump badging dump xmltree",
        examples=[("Badging", "aapt dump badging app.apk")], deps=[]),
    "zipalign": dict(
        category="apk-inspection", subcategory="alignment", host_device="host",
        input_types=["apk"], output_types=["apk"],
        capabilities=["page-align native libs (-p 4)", "verify alignment (-c -p 4)"],
        install_method="download", install_command="sdkmanager build-tools;35.0.0",
        verification="zipalign (no args prints usage)", common_flags="-p 4 -c -v",
        examples=[("Align", "zipalign -p 4 in.apk out.apk"),
                  ("Check", "zipalign -c -p 4 out.apk")], deps=[]),
    "apksigner": dict(
        category="apk-inspection", subcategory="signing", host_device="host",
        input_types=["apk"], output_types=["apk", "report"],
        capabilities=["sign APK (v1/v2/v3/v4 schemes)", "verify signatures & print cert SHA-256"],
        install_method="download", install_command="sdkmanager build-tools;35.0.0",
        verification="apksigner --version", common_flags="sign --ks k.jks verify",
        examples=[("Sign", "apksigner sign --ks k.jks --ks-pass pass:android app.apk"),
                  ("Verify", "apksigner verify --print-certs app.apk")],
        deps=["java", "zipalign"]),
    "dexdump": dict(
        category="dex-analysis", subcategory="dex-header", host_device="host",
        input_types=["dex"], output_types=["text", "report"],
        capabilities=["list classes/methods of a dex", "header/statistics dump"],
        install_method="download", install_command="sdkmanager build-tools;35.0.0",
        verification="dexdump -h", common_flags="-d -f",
        examples=[("Class list", "dexdump -f classes.dex | findstr Class")], deps=[]),
    "git": dict(
        category="other", subcategory="vcs", host_device="host",
        input_types=["directory"], output_types=["report"],
        capabilities=["version snapshots of knowledge base state"],
        install_method="download", install_command="git (default install)",
        verification="git --version", common_flags="add commit status",
        examples=[("Status", "git status")], deps=[]),
    "capstone": dict(
        category="native-analysis", subcategory="disassembler", host_device="host",
        input_types=["so", "binary"], output_types=["text", "report"],
        capabilities=["disassemble ARM64/ARM/x86 machine code",
                      "string xref scans over .text", "instruction-level RE of packer stubs"],
        install_method="pip", install_command="pip install capstone",
        verification="python -c \"import capstone; print(capstone.__version__)\"",
        common_flags="CS_ARCH_ARM64 detail=on",
        examples=[("Disasm", "python -c \"from capstone import *; ...\"")], deps=[]),
    "pycryptodome": dict(
        category="static-analysis", subcategory="crypto-library", host_device="host",
        input_types=["binary", "so"], output_types=["binary"],
        capabilities=["AES/ECB/CBC/GCM, XOR, RC4 primitives for payload decryption"],
        install_method="pip", install_command="pip install pycryptodome",
        verification="python -c \"import Crypto; print(Crypto.__version__)\"",
        common_flags="AES.new(key, AES.MODE_ECB)",
        examples=[("AES", "AES.new(key, AES.MODE_ECB).decrypt(blob)")], deps=[]),
    "cryptography": dict(
        category="static-analysis", subcategory="crypto-library", host_device="host",
        input_types=["binary"], output_types=["binary"],
        capabilities=["AES-GCM/CBC high-level decrypt, X.509 cert inspection"],
        install_method="pip", install_command="pip install cryptography",
        verification="python -c \"import cryptography; print(cryptography.__version__)\"",
        common_flags="Fernet / Cipher / GCM",
        examples=[("GCM", "from cryptography.hazmat.primitives.ciphers.aead import AESGCM")],
        deps=[]),
    "pyyaml": dict(
        category="other", subcategory="kb-parser", host_device="host",
        input_types=["directory"], output_types=["json"],
        capabilities=["parses YAML frontmatter for graph/index generation"],
        install_method="pip", install_command="pip install pyyaml",
        verification="python -c \"import yaml; print(yaml.__version__)\"",
        common_flags="safe_load",
        examples=[("Parse", "yaml.safe_load(fm_text)")], deps=[]),
    "frida": dict(
        category="dynamic-observation", subcategory="instrumentation", host_device="both",
        input_types=["process", "apk", "so"], output_types=["log", "json"],
        capabilities=["runtime Java/native hooking", "method argument/result capture",
                      "bypass SSL pinning & anti-debug at runtime"],
        install_method="pip", install_command="pip install frida-tools (+ pushed frida-server on device)",
        verification="python -c \"import frida; print(frida.__version__)\"",
        common_flags="-U -f pkg -l script.js",
        examples=[("Spawn", "frida -U -f pokemon.dex.guard -l hook.js")],
        deps=["adb"]),
}

DEVICE_TOOL_PROBE = ["su", "toybox", "busybox", "sqlite3", "strace", "tcpdump", "frida", "objection"]


def _run(cmd: list[str], timeout: int = 25) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:
        return 125, str(e)


def _expand(cand: str) -> list[str]:
    if any(ch in cand for ch in ("*", "?")):
        expanded = os.path.expandvars(cand)
        return sorted(globmod.glob(expanded), reverse=True)
    return [os.path.expandvars(cand)]


def resolve_path(candidates: list[str]) -> str | None:
    for cand in candidates:
        if os.sep in cand or (HOST and "\\" in cand) or cand.endswith((".jar", ".exe", ".bat", ".cmd")):
            for p in _expand(cand):
                if Path(p).exists():
                    return str(Path(p))
        else:
            found = shutil.which(cand)
            if found:
                return found
            for p in _expand(cand):
                if Path(p).exists():
                    return str(Path(p))
    return None


def find_java() -> str | None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for t in cfg["tools"]:
        if t["key"] == "java":
            return resolve_path(t["search"])
    return shutil.which("java")


def probe_version(spec: dict, path: str) -> tuple[str | None, str]:
    out = ""
    if spec.get("module"):
        try:
            dist = spec.get("distribution", spec["key"])
            return imd.version(dist), f"importlib.metadata.version('{dist}')"
        except Exception as e:
            return None, f"module probe failed: {e}"
    if spec.get("jar"):
        java = find_java()
        if not java:
            return None, "java runtime missing"
        cmd = [java, "-jar", path] + spec.get("version_args", ["--version"])
    else:
        cmd = [path] + spec.get("version_args", [])
    rc, out = _run(cmd)
    if not out:
        # some tools (zipalign) identify themselves by path folder name
        m = re.search(r"build-tools[\\/](\d+\.\d+\.\d+)", path)
        return (m.group(1), f"version from build-tools path (exit {rc}, no output)") if m else (None, f"no version output (exit {rc})")
    first_line = out.splitlines()[0][:200]
    rx = spec.get("version_regex")
    if rx:
        m = re.search(rx, out)
        if m:
            val = m.group(1) if m.groups() else m.group(0)
            if re.match(r"^v?\d", val):
                return val, first_line
    mp = re.search(r"build-tools[\\/](\d+\.\d+\.\d+)", path)
    if mp:
        return mp.group(1), f"build-tools {mp.group(1)} (output: {first_line})"
    return first_line[:60], first_line


def load_registry() -> dict:
    """key -> {tool_id, version, availability, article} from wiki/tool-registry."""
    reg = {}
    if not REGISTRY_DIR.is_dir():
        return reg
    for md in REGISTRY_DIR.glob("*.md"):
        if md.name.startswith("_"):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        fm = {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm[k.strip()] = v.strip().strip('"').strip("'")
        key = fm.get("name", md.stem).lower()
        tid = fm.get("tool_id")
        if tid:
            reg[key] = {"tool_id": tid, "version": fm.get("version"),
                        "availability": fm.get("availability"), "article": md, "key": fm.get("key", "")}
            if fm.get("key"):
                reg[fm["key"]] = reg[key]
    return reg


def discover(write: bool = False, serial: str | None = None, config_path: Path = CONFIG_PATH) -> list[dict]:
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    registry = load_registry()
    maxima = kb_ids.scan(kb_ids.kb_root() / "vault" / "articles")
    next_tr = maxima.get("TR", 0) + 1
    records = []

    for spec in cfg["tools"]:
        path = None if spec.get("module") else resolve_path(spec.get("search", [spec["key"]]))
        if spec.get("module") or path:
            version, vdetail = probe_version(spec, path or spec["key"])
        else:
            version, vdetail = None, "not found on PATH or in known locations"
        available = bool(version) or (spec.get("module") and path is None and vdetail.startswith("importlib.metadata.version") and version)
        availability = "available" if available else "missing"

        meta = TOOL_META.get(spec["key"], {})
        reg_key = spec["key"]
        existing = registry.get(reg_key) or registry.get(spec.get("name", "").lower())
        tool_id = existing["tool_id"] if existing else None
        change = "unchanged"
        if not existing:
            change = "new" if availability == "available" else "missing-new"
            if availability == "available":
                tool_id = f"TR-{next_tr:04d}"
                next_tr += 1
        else:
            if existing.get("version") != version:
                change = "updated"

        install_needed = availability != "available"
        records.append({
            "tool_id": tool_id, "key": spec["key"], "name": spec.get("name", spec["key"]),
            "version": version, "path": path or (spec["key"] if spec.get("module") else None),
            "category": meta.get("category", "other"), "subcategory": meta.get("subcategory", ""),
            "host_device": meta.get("host_device", "host"),
            "availability": availability, "change": change, "version_detail": vdetail,
            "meta": meta, "install_method": meta.get("install_method", ""),
            "install_command": meta.get("install_command", ""),
        })

    # NOTE: device-side tools are volatile state - probed at runtime by
    # env_probe.py (JSON only) and NEVER persisted as registry articles.
    return records


def article_for(rec: dict) -> str:
    m = rec["meta"]
    tid = rec["tool_id"] or "TR-XXXX"
    caps = m.get("capabilities", [])
    inputs = m.get("input_types", ["binary"])
    outputs = m.get("output_types", ["text"])
    verified_arch = "Yes" if rec["key"] in {"adb", "apktool", "aapt", "zipalign", "apksigner", "jadx", "dexdump", "capstone", "java"} else "No"
    install_cmd = rec.get("install_command") or "N/A (available)"
    dep_rows = "\n".join(f"| {d} | — | Yes | — |" for d in m.get("deps", [])) or "| — | — | — | — |"
    examples = ""
    for i, (title, cmd) in enumerate(m.get("examples", [])[:2], 1):
        examples += f"""### Example {i}: {title}
```bash
{cmd}
```
**Input:** see capabilities  **Output:** see output types
**When to Use:** routine {rec['name']} workflow

"""
    cap_rows = "\n".join(f"| `{c}` | `{c}` | No |" for c in caps) or "| `probe` | version probe only | Yes |"
    io_rows = "\n".join(f"| Input | `{t}` | — | — |" for t in inputs)
    io_rows += "\n" + "\n".join(f"| Output | `{t}` | — | — |" for t in outputs)
    missing_note = ""
    if rec["availability"] != "available":
        missing_note = f"""
**Method:** `{rec.get('install_method') or 'unknown'}`
**Command:** `{rec.get('install_command') or 'see notes'}`
**Notes:** tool currently **{rec['availability']}** — install before use.
"""
    return f"""---
type: tool-registry
topic: wiki/tool-registry/_index
source: .kb/scripts/tool_discover.py
tags: [tool, {rec['category']}, {rec['subcategory'] or 'misc'}]
complexity: beginner
completeness: complete
last_verified: {TODAY}
tool_versions: [{rec['name']} {rec['version'] or 'n/a'}]
tool_id: {tid}
key: {rec['key']}
name: {rec['name']}
version: {rec['version'] or ''}
path: "runtime-discovered (host paths never stored)"
category: {rec['category']}
subcategory: {rec['subcategory']}
host_device: {rec['host_device']}
input_types: {json.dumps(inputs)}
output_types: {json.dumps(outputs)}
capabilities: {json.dumps(caps)}
configuration: "{m.get('common_flags', 'default')}"
timeout_seconds: 120
verification_methods: [{json.dumps(m.get('verification', ''))}]
availability: {rec['availability']}
install_method: {rec.get('install_method') or 'N/A'}
install_command: "{rec.get('install_command') or ''}"
install_notes: "{'' if rec['availability'] == 'available' else 'missing on this host'}"
dependencies: {json.dumps(m.get('deps', []))}
known_issues: []
works_on_architectures: [arm64-v8a, armeabi-v7a, x86, x86_64]
works_on_android: [all]
llm_summary: "{rec['name']} {rec['version'] or '(missing)'} — {', '.join(caps[:2]) or rec['category']}. {'Use for ' + rec['category'] + ' tasks.'}"
---

# Tool: {tid} — {rec['name']}

## This Article Answers
- "What does {rec['name']} do?"
- "When should I use {rec['name']}?"
- "How do I install/verify {rec['name']}?"
- "What are {rec['name']}'s limitations?"

## Key Takeaways
- [PURPOSE] {caps[0] if caps else rec['name']}
- [CATEGORY] {rec['category']} / {rec['subcategory']}
- [INPUTS] {', '.join(inputs)}
- [OUTPUTS] {', '.join(outputs)}
- [AVAILABILITY] {rec['availability']}

## Basic Information
| Property | Value |
|---|---|
| Tool ID | {tid} |
| Name | `{rec['name']}` |
| Version | `{rec['version'] or 'not installed'}` |
| Path | runtime-discovered (never stored) |
| Category | `{rec['category']}` |
| Subcategory | `{rec['subcategory']}` |
| Host/Device | {rec['host_device']} |
| Availability | {rec['availability']} |

## Capabilities
| Capability | Description | Verified |
|---|---|---|
{cap_rows}

## Input/Output Types
| Direction | Type | Format | Notes |
|---|---|---|---|
{io_rows}

## Installation
**Method:** `{rec.get('install_method') or 'N/A'}`
**Command:** `{install_cmd}`{missing_note}
**Verification Command:** `{m.get('verification', 'n/a')}`
**Expected Output:** version string `{rec['version'] or '?'}`

## Configuration
**Default Config:** `{m.get('common_flags', 'default')}`
**Common Flags:** `{m.get('common_flags', '')}`
**Environment Variables:** `PATH` (absolute paths are runtime-only, never stored)

## Usage Examples
{examples}
## Compatibility
| Architecture | Supported | Tested |
|---|---|---|
| arm64-v8a | Yes | {verified_arch} |
| armeabi-v7a | Yes | {verified_arch} |
| x86 | Yes | {verified_arch} |
| x86_64 | Yes | {verified_arch} |

| Android API | Supported | Tested |
|---|---|---|
| 21-23 | Yes | No |
| 24-28 | Yes | No |
| 29-30 | Yes | No |
| 31-33 | Yes | No |
| 34+ | Yes | No |

## Known Issues
| Issue | Severity | Workaround | Status |
|---|---|---|---|
| — | — | — | — |

## Dependencies
| Tool ID | Name | Required | Version Constraint |
|---|---|---|---|
{dep_rows}

## Performance
| Metric | Value | Conditions |
|---|---|---|
| Typical Runtime | `<tool-dependent>` | small APK (<50 MB) |
| Memory Usage | `<tool-dependent>` | default flags |
| Output Size | `<tool-dependent>` | — |

## Verification Methods
| Method | Description | Command |
|---|---|---|
| version-probe | output matches `{rec['version'] or 'n/a'}` | `{m.get('verification', 'n/a')}` |

## What This Article Does NOT Cover
- Which techniques use this tool in sequence — see [[wiki/techniques/_index]]
- Availability history is runtime-only — run `.kb/scripts/tool_discover.py` (volatile device/host state is never stored)

## Open Questions / Unverified Claims
- Auto-generated by tool_discover; compatibility "Tested" flags reflect known sessions only.

## Related
- [[wiki/techniques/_index]] — techniques requiring this tool
- [[wiki/tool-registry/_index]] — registry index
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Discover tools and maintain the Tool Registry.")
    ap.add_argument("--write", action="store_true", help="write/update wiki/tool-registry articles")
    ap.add_argument("--markdown", action="store_true", help="summary table instead of JSON")
    ap.add_argument("--serial", help="adb serial (device tools are probed at runtime by env_probe and never stored)")
    ap.add_argument("--config", help="alternate tools.config.json")
    args = ap.parse_args()

    cfg_path = Path(args.config) if args.config else CONFIG_PATH
    try:
        records = discover(write=args.write, serial=args.serial, config_path=cfg_path)
    except Exception as e:
        print(json.dumps({"error": f"discovery failed: {e}"}))
        return 4

    if args.write:
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        written, updated = [], []
        for rec in records:
            if not rec["tool_id"] or rec.get("host_device") == "device":
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", rec["name"].lower()).strip("-")[:32]
            path = REGISTRY_DIR / f"{rec['tool_id']}-{slug}.md"
            existed = path.exists()
            path.write_text(article_for(rec), encoding="utf-8")
            (updated if existed else written).append(path.name)
        print(json.dumps({"written": written, "updated": updated,
                          "registry_dir": str(REGISTRY_DIR)}, indent=2))
        return 0

    if args.markdown:
        print("| Tool ID | Name | Version | Category | Availability | Change |")
        print("|---|---|---|---|---|---|")
        for r in records:
            print(f"| {r['tool_id'] or '—'} | {r['name']} | {r['version'] or '—'} | "
                  f"{r['category']} | {r['availability']} | {r['change']} |")
        return 0

    slim = [{k: v for k, v in r.items() if k != "meta"} for r in records]
    print(json.dumps(slim, indent=2))
    avail = sum(1 for r in records if r["availability"] == "available")
    return 0 if avail else 5


if __name__ == "__main__":
    sys.exit(main())
