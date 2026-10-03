#!/usr/bin/env python3
"""
Environment probe - builds a runtime EnvironmentProfile as JSON.
Runtime-only by design: device state is NEVER written into the KB
(Iron Rule 6); use the health verdict + record `host-runtime` in artifacts.

Performs the mandatory health checks BEFORE any APK is analyzed:

    ADB availability · device responsiveness · root access · shell access ·
    required directories · host tools · device tools · disk space · boot state

Anything that fails is classified ENVIRONMENT_ISSUE (not APK_FAILURE).

Usage:
    python env_probe.py                          # JSON profile to stdout
    python env_probe.py --adb PATH --serial SER  # explicit adb/device
    # NOTE: runtime-only - device state is NEVER written into the KB
    # (Iron Rule 6): no --write/--markdown modes exist on purpose.
    python env_probe.py --health                 # one-line health verdict + failing checks

Exit codes: 0 = READY, 2 = DEGRADED, 3 = UNAVAILABLE, 4 = ENVIRONMENT_ISSUE (probe error)
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tool_discover  # noqa: E402  (same-directory helper)

HOST = os.name == "nt"

ADB_KNOWN = [
    os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
    os.path.expandvars(r"%ANDROID_HOME%\platform-tools\adb.exe"),
    os.path.expandvars(r"%ANDROID_SDK_ROOT%\platform-tools\adb.exe"),
    "/home/*/Android/Sdk/platform-tools/adb",
    "/opt/android-sdk/platform-tools/adb",
]

DEVICE_TOOLS = ["su", "toybox", "busybox", "sqlite3", "strace", "tcpdump", "frida", "objection"]


def find_adb(explicit: str | None) -> str | None:
    if explicit:
        return explicit if Path(explicit).exists() else None
    for cand in ADB_KNOWN:
        if "*" in cand:
            for expanded in sorted(Path("/").glob(cand.lstrip("/"))):
                if expanded.exists():
                    return str(expanded)
            continue
        if Path(cand).exists():
            return cand
    return shutil.which("adb")


def run(cmd: list[str], timeout: int = 30, shell: bool = False) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=shell,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "executable not found"
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:  # ENVIRONMENT_ISSUE, never crashes the probe
        return 125, f"probe error: {e}"


def probe(adb: str | None, serial: str | None) -> dict:
    checks: list[dict] = []
    connect_candidates = ["127.0.0.1:16416", "127.0.0.1:7555", "127.0.0.1:5555"]

    def add(name: str, ok: bool, details: str, required: bool = True):
        checks.append({
            "check": name,
            "status": "PASS" if ok else ("FAIL" if required else "SKIP"),
            "details": details[:500],
        })
        return ok

    profile = {
        "environment_id": None,
        "name": None,
        "device_type": "emulator",
        "device_name": "unknown",
        "adb_available": False,
        "adb_path": None,
        "adb_version": None,
        "connected_devices": [],
        "target_device": None,
        "android_version": None,
        "api_level": None,
        "architecture": None,
        "root_available": False,
        "root_method": None,
        "shell_access": False,
        "shell_uid": None,
        "selinux": None,
        "writable_paths": [],
        "host_tools": [],
        "device_tools": [],
        "available_storage_gb": None,
        "emulator_state": "unknown",
        "status": "UNAVAILABLE",
        "issue_class": None,
        "detection_timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "checks": checks,
    }

    # --- ADB availability ------------------------------------------------
    adb_path = find_adb(adb)
    if adb_path:
        rc, out = run([adb_path, "version"])
        m = re.search(r"(\d+\.\d+\.\d+)", out)
        profile["adb_available"] = rc == 0
        profile["adb_path"] = adb_path
        profile["adb_version"] = m.group(1) if m else "unknown"
        add("ADB available", rc == 0, f"{adb_path} -> {out.splitlines()[0] if out else 'no output'}")
    else:
        add("ADB available", False, "adb not found on PATH or in known SDK locations")
        profile["issue_class"] = "ENVIRONMENT_ISSUE"
        profile["status"] = "UNAVAILABLE"
        return profile

    adb_cmd = [adb_path]
    rc, out = run(adb_cmd + ["devices"])
    devices = []
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) == 2 and parts[1].strip() == "device":
            devices.append(parts[0].strip())
    # no emulator attached yet: try known local emulator ports (MuMu etc.)
    if not any(d.startswith("127.0.0.1") for d in devices):
        for cand in connect_candidates:
            run(adb_cmd + ["connect", cand], timeout=8)
        rc, out = run(adb_cmd + ["devices"])
        devices = [line.split("\t")[0].strip() for line in out.splitlines()[1:]
                   if len(line.split("\t")) == 2 and line.split("\t")[1].strip() == "device"]
    # privacy: physical serials are never persisted (raw `devices` kept for targeting only)
    profile["connected_devices"] = [
        d if d.startswith(("127.0.0.1", "emulator")) else "REDACTED" for d in devices]
    if serial:
        target = serial if serial in devices else None
    else:
        local = [d for d in devices if d.startswith("127.0.0.1")]
        target = (local or devices)[0] if (local or devices) else None

    if not target:
        shown = [d if d.startswith(("127.0.0.1", "emulator")) else "REDACTED" for d in devices]
        add("Device responsive", False, f"no device in 'device' state (found: {shown or 'none'})")
        profile["issue_class"] = "ENVIRONMENT_ISSUE"
        profile["status"] = "UNAVAILABLE"
        return profile

    profile["target_device"] = (
        target if target.startswith(("127.0.0.1", "emulator")) else "REDACTED")
    adb_cmd = [adb_path, "-s", target]

    def ashell(args: list[str], timeout: int = 30) -> tuple[int, str]:
        return run(adb_cmd + ["shell"] + args, timeout=timeout)

    # --- Device responsive ----------------------------------------------
    rc, out = ashell(["echo", "ok"])
    responsive = rc == 0 and "ok" in out
    add("Device responsive", responsive, f"shell echo -> {out[:120]}")
    if not responsive:
        profile["issue_class"] = "ENVIRONMENT_ISSUE"
        profile["status"] = "UNAVAILABLE"
        return profile
    profile["emulator_state"] = "running"

    # --- Properties -------------------------------------------------------
    def prop(name: str) -> str | None:
        rc, out = ashell(["getprop", name])
        return out.strip() if rc == 0 and out.strip() else None

    profile["android_version"] = prop("ro.build.version.release")
    api = prop("ro.build.version.sdk")
    profile["api_level"] = int(api) if api and api.isdigit() else None
    profile["architecture"] = prop("ro.product.cpu.abi")
    model = prop("ro.product.model") or "unknown"
    manufacturer = prop("ro.product.manufacturer") or "unknown"
    product = prop("ro.product.name") or ""
    profile["device_name"] = model
    # Emulators are detected by the local adb serial: device props are spoofed
    # (MuMu reports a real Samsung model/product name, no qemu props).
    local_serial = target.startswith("127.0.0.1") or target.startswith("emulator")
    keyword_hit = any(k in (product + model + manufacturer).lower()
                      for k in ("mumu", "emulator", "vbox", "genymotion", "goldfish", "ranchu"))
    is_emulator = local_serial or keyword_hit
    is_mumu = is_emulator and ("mumu" in (product + model).lower()
                               or (product or "").lower() in ("a55x", "vbox86p", "nx")
                               or local_serial)
    if is_emulator:
        profile["device_name"] = "MuMu" if is_mumu else f"Emulator ({model})"
    else:
        # privacy: never persist physical-device identifying props
        model, manufacturer, product = "Physical Device", "unknown", "physical"
        profile["device_name"] = "Physical Device"
    profile["device_detail"] = {
        "manufacturer": manufacturer, "model": model, "product": product,
        "build_id": prop("ro.build.id"), "security_patch": prop("ro.build.version.security_patch"),
        "is_emulator": is_emulator,
        "emulator_detected_via": ("adb-local-serial" if local_serial else "build-property") if is_emulator else None,
    }
    profile["device_type"] = "emulator" if is_emulator else "physical"
    add("Device properties", bool(profile["android_version"]),
        f"Android {profile['android_version']} / API {profile['api_level']} / {profile['architecture']} / {profile['device_type']}")

    # --- Shell access / UID ---------------------------------------------
    rc, out = ashell(["id"])
    profile["shell_access"] = rc == 0
    m = re.search(r"uid=(\d+)", out)
    profile["shell_uid"] = int(m.group(1)) if m else None
    add("Shell access", rc == 0, out[:200])

    # --- Root -------------------------------------------------------------
    rc, out = ashell(["su", "-c", "id"], timeout=20)
    root_ok = rc == 0 and "uid=0" in out
    method = None
    if root_ok:
        method = "su"
    else:
        if profile["shell_uid"] == 0:
            root_ok, method = True, "shell-is-root"
        else:
            rc2, out2 = ashell(["id"])
            if rc2 == 0 and "uid=0" in out2:
                root_ok, method = True, "direct-root-shell"
    profile["root_available"] = root_ok
    profile["root_method"] = method
    add("Root access", root_ok, out[:200] if root_ok else f"su -c id -> {out[:150]}")

    rc, out = ashell(["getenforce"])
    profile["selinux"] = out.strip() if rc == 0 and out.strip() else None

    # --- Boot state -------------------------------------------------------
    rc, out = ashell(["getprop", "sys.boot_completed"])
    booted = out.strip() == "1"
    add("Emulator boot state", booted, f"sys.boot_completed={out.strip() or 'empty'}")

    # --- Required/writable directories ------------------------------------
    for path in ["/data/local/tmp", "/sdcard"]:
        rc, out = ashell([f"echo probe > {path}/.env_probe && cat {path}/.env_probe && rm -f {path}/.env_probe"])
        ok = rc == 0 and "probe" in out
        if ok:
            profile["writable_paths"].append(path)
        add(f"Writable: {path}", ok, out[:120] or "no output")
    # root-only probe (records capability, not required for READY)
    if root_ok:
        rc, out = ashell(["su", "-c", "echo rootok"])
        add("Root-writable probe", rc == 0 and "rootok" in out, out[:120], required=False)

    # --- Disk space ---------------------------------------------------------
    rc, out = ashell(["df", "-k", "/data"])
    gb = None
    if rc == 0:
        lines = [ln for ln in out.splitlines() if ln.strip() and not ln.startswith("Filesystem")]
        if lines:
            parts = lines[0].split()
            if len(parts) >= 4 and parts[3].isdigit():
                gb = round(int(parts[3]) / 1024 / 1024, 2)
    profile["available_storage_gb"] = gb
    add("Disk space (/data)", gb is not None and gb > 0.5, f"{gb} GB available" if gb else "unable to parse df")

    # --- Device tools ---------------------------------------------------------
    present = []
    for t in DEVICE_TOOLS:
        rc, out = ashell(["which", t])
        if rc == 0 and out.strip():
            present.append(t)
    profile["device_tool_names"] = present
    try:
        reg = tool_discover.load_registry()
        ids = [reg[f"device-{t}"]["tool_id"] for t in present if f"device-{t}" in reg]
    except Exception:
        ids = []
    profile["device_tools"] = ids or present
    add("Device tools", True, f"present: {present or 'none beyond toybox basics'}", required=False)

    # --- Host tools (delegates to tool_discover) -------------------------------
    try:
        tools = tool_discover.discover(write=False)
        profile["host_tools"] = [t["tool_id"] for t in tools if t.get("availability") == "available"]
        profile["host_tool_details"] = tools
        add("Host tools", len(profile["host_tools"]) > 0,
            f"{len(profile['host_tools'])} available: {', '.join(profile['host_tools'])}")
    except Exception as e:
        add("Host tools", False, f"tool_discover failed: {e}", required=False)

    # --- Host analysis directories -------------------------------------------
    repo = Path(__file__).resolve().parent.parent.parent
    host_dirs = {"repo_root": str(repo), "wiki": str(repo / "vault" / "articles")}
    ok = os.access(repo, os.W_OK)
    host_dirs["writable"] = ok
    profile["host_dirs"] = host_dirs
    add("Required directories (host)", ok, f"wiki writable={ok}")

    # --- Verdict ----------------------------------------------------------------
    failed_required = [c for c in checks if c["status"] == "FAIL"]
    if not failed_required:
        profile["status"] = "READY"
        profile["issue_class"] = None
    elif not profile["root_available"] and all(
            c["check"] != "Root access" for c in failed_required):
        profile["status"] = "READY"
        profile["issue_class"] = None
    else:
        only_root_failed = all(c["check"] == "Root access" for c in failed_required)
        profile["status"] = "DEGRADED" if only_root_failed else "UNAVAILABLE"
        profile["issue_class"] = "ENVIRONMENT_ISSUE"

    # environment id: stable slug + root marker (immutable profiles get -vN on write)
    if is_mumu:
        slug = "mumu"
    elif is_emulator:
        slug = "emulator"
    else:
        slug_src = (product or model or manufacturer).lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug_src).strip("-") or "device"
    profile["environment_id"] = f"{slug}-{'rooted' if root_ok else 'noroot'}-001"
    profile["name"] = f"{profile['device_name']} ({profile['device_type']}, Android {profile['android_version']}, {profile['architecture']})"
    # privacy: physical adb serials are never persisted (all commands already ran)
    profile["connected_devices"] = [
        d if d.startswith(("127.0.0.1", "emulator")) else "REDACTED"
        for d in profile.get("connected_devices", [])]
    if not str(profile.get("target_device", "")).startswith(("127.0.0.1", "emulator")):
        profile["target_device"] = "REDACTED"
    return profile


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe the analysis environment (EnvironmentProfile).")
    ap.add_argument("--adb", help="path to adb")
    ap.add_argument("--serial", help="device serial to target")
    ap.add_argument("--health", action="store_true", help="one-line health verdict")
    args = ap.parse_args()

    try:
        profile = probe(args.adb, args.serial)
    except Exception as e:
        print(json.dumps({"issue_class": "ENVIRONMENT_ISSUE", "error": str(e)}))
        return 4

    if args.health:
        fails = [c for c in profile["checks"] if c["status"] == "FAIL"]
        print(f"{profile['status']} ({profile['issue_class'] or 'no issue'}) - "
              + ("all checks passed" if not fails else
                 "; ".join(f"{c['check']}: {c['details']}" for c in fails)))
        return {"READY": 0, "DEGRADED": 2}.get(profile["status"], 3)



    print(json.dumps(profile, indent=2))
    return {"READY": 0, "DEGRADED": 2}.get(profile["status"], 3)


if __name__ == "__main__":
    sys.exit(main())
