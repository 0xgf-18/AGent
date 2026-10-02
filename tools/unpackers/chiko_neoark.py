#!/usr/bin/env python3
"""
chiko_neoark.py — fast-path unpacker for Chiko / NeoArk (Art-Jiagu family).

Implements the method recorded in `knowledge_base/wiki/packers/chiko-neoark.md`
(v2, confidence 0.95, evidence EXP-0002 + EXP-0003), step for step. Constants are
the observed values from those experiments; see the article for provenance.

    python scripts/packers/chiko_neoark.py <apk> [--offline|--device] [--serial S]

Two paths, both documented in the article:

  offline  Step 3,5,6,7,8 -- host only, no device, no root. Recovers the
           PRIMARY blob via a 64-byte repeating XOR key. Observed result: one
           9,303,180 B dex. It does NOT recover the other blobs: EXP-0002 proved
           they use different keys and resisted column-mode recovery at all 64
           rotations. If you need the whole app, use --device.

  device   Step 1 (T-0021 -> T-0010) -- rooted device required. Recovers ALL
           blobs by dumping [anon:dalvik-DEX data] out of /proc/<pid>/mem.
           Observed result: 4 dex, 6,738 class_defs, the real app logic.

The script reports what it actually got. It never claims the app is unpacked
when it only recovered a helper component -- that exact mistake is Step 8, and
EXP-0002 fell into it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import (  # noqa: E402
    EXIT_COMMAND_SUCCESS, EXIT_ENVIRONMENT, EXIT_FAILED, EXIT_OK,
    Fingerprint, Gate, _say, carve_dex, fail, find_java, find_tool, ok,
    output_paths, require_fingerprint, require_tool, run, scratch, step,
    validate_dex, warn, main_wrapper,
)

PACKER = "chiko-neoark"

# --- observed constants, verbatim from the article / experiments -------------
STUB_SO = "libchikoStub.so"          # packer-owned decryptor, drop on rebuild
LOAD_LIBRARY_ARG = "chikoStub"       # System.loadLibrary("chikoStub")
ARK_CLASS_HINT = "b2al/encryp/vip"   # obfuscated Application class
LOADER_STRINGS = (                  # strings inside the decryptor .so
    b"ark_payload_%d.dex",
    b"ark_code_cache",
    b"com/ark/safe/StubApp",
)
OBSERVED_PERIOD = 64                # EXP-0002: autocorrelation spike at lag 64
OBSERVED_SPIKE = 0.5085             # 50.85% at lag 64, all others <= 1.85%
OBSERVED_FLAT = 0.0185
APPEND_MIN = 1 << 20                 # >1 MB appended => packed (Step 3)
SHELL_MAX_DATA_END = 0x1000          # data_off+data_size ~= 0x3a4 observed
SHELL_MAX_CLASS_DEFS = 2
DECOY_MAX = 1024                     # decoy asset is 91 B (Step 2)


# ==========================================================================
# fingerprint
# ==========================================================================
def fingerprint(apk: Path) -> Fingerprint:
    """Steps 2 + 3 + 4 of the article: disarm the decoy, confirm the appended
    payload, confirm the loader .so. Strong checks must ALL hit."""
    fp = Fingerprint(PACKER)
    with zipfile.ZipFile(apk) as z:
        names = z.namelist()

        # --- Step 2: a *jiagu* asset here is a decoy, not 360 jiagu ---
        jiagu = [n for n in names if "jiagu" in n.lower()]
        for n in jiagu:
            raw = z.read(n)
            texty = all(32 <= b < 127 or b in (9, 10, 13) for b in raw)
            fp.weak.append((
                f"decoy marker asset {n}",
                len(raw) < DECOY_MAX and texty,
                f"{len(raw)} B, ascii={texty} -> decoy, NOT 360 jiagu",
            ))

        # --- Step 4: the packer-owned decryptor .so is the hard tell ---
        stubs = [n for n in names if n.endswith(STUB_SO)]
        so_strings: list[bytes] = []
        for n in stubs:
            raw = z.read(n)
            so_strings += [s for s in LOADER_STRINGS if s in raw]
        fp.strong.append((
            f"{STUB_SO} present",
            bool(stubs),
            ", ".join(stubs) if stubs else "not found -- not Chiko/NeoArk",
        ))
        fp.strong.append((
            "loader .so carries ark/StubApp strings",
            bool(so_strings),
            ", ".join(s.decode() for s in so_strings) or "none present",
        ))

        # --- Step 3: shell dex with a huge appended payload ---
        try:
            shell = z.read("classes.dex")
        except KeyError:
            shell = b""
        appended = 0
        if len(shell) >= 0x70:
            data_off, = struct.unpack_from("<I", shell, 0x6C)
            data_size, = struct.unpack_from("<I", shell, 0x68)
            file_size, = struct.unpack_from("<I", shell, 0x20)
            class_defs, = struct.unpack_from("<I", shell, 0x60)
            string_ids, = struct.unpack_from("<I", shell, 0x38)
            data_end = data_off + data_size
            appended = max(0, file_size - data_end)
            fp.strong.append((
                f"appended payload past every DEX section ({appended:,} B)",
                appended > APPEND_MIN and data_end < SHELL_MAX_DATA_END,
                f"data_off+data_size={data_end:#x} ({data_end}) "
                f"file_size={file_size:,} class_defs={class_defs} strings={string_ids}",
            ))
            fp.weak.append((
                "shell dex is a loader (tiny class count)",
                0 < class_defs <= SHELL_MAX_CLASS_DEFS and string_ids < 32,
                f"class_defs={class_defs}, string_ids={string_ids}",
            ))
        else:
            fp.strong.append(("classes.dex readable", False, "missing or truncated"))

        # --- the obfuscated Application class in the manifest ---
        man = z.read("AndroidManifest.xml") if "AndroidManifest.xml" in names else b""
        dotted = ARK_CLASS_HINT.replace("/", ".")
        in_pool = dotted.encode() in man or ARK_CLASS_HINT.encode() in man
        app_cls, pkg = _manifest_app_class(apk)
        outside = bool(app_cls and pkg and not app_cls.startswith(pkg + "."))
        fp.weak.append((
            f"manifest application android:name obfuscated (e.g. {dotted})",
            in_pool or outside,
            f"string-pool hit={in_pool}; android:name={app_cls!r} "
            f"package={pkg!r} outside-package={outside}",
        ))
    return fp


def _manifest_app_class(apk: Path) -> tuple[str | None, str | None]:
    """Return (<application android:name>, <package>) from the binary manifest.

    aapt2 dump xmltree prints resolved attribute values, so this works on the
    compiled binary XML without needing a decoder. Falls back to the string
    pool, which is where the dotted class name lives even when the attribute
    cannot be resolved.
    """
    aapt2 = find_tool("aapt2")
    if aapt2:
        import re
        p = subprocess.run([aapt2, "dump", "xmltree", str(apk), "--file",
                            "AndroidManifest.xml"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        pkg, app_cls = None, None
        cur = None
        for line in p.stdout.splitlines():
            s = line.strip()
            if s.startswith("E: application"):
                cur = "app"
            elif s.startswith("E: ") and "manifest" not in s:
                cur = None
            elif cur == "app" and "android:name" in s and app_cls is None:
                m = re.search(r'\(0x[0-9a-f]+\)="([^"]+)"', s)
                if m:
                    app_cls = m.group(1)
            m = re.search(r'package="([^"]+)"', s)
            if m and pkg is None:
                pkg = m.group(1)
        if app_cls:
            return app_cls, pkg
    return None, None


# ==========================================================================
# offline path -- Steps 3, 5, 6, 7, 8
# ==========================================================================
def autocorrelation(buf: bytes, max_lag: int = 512, sample: int = 200_000) -> list[tuple[int, float]]:
    """Step 5: match-index autocorrelation. A repeating-key XOR spikes at the
    key period and its multiples; real encryption stays flat near 1/256."""
    s = buf[:sample]
    out = []
    for lag in range(1, max_lag + 1):
        if lag >= len(s):
            break
        a = s[:-lag]
        b = s[lag:]
        hits = sum(1 for x, y in zip(a, b) if x == y)
        out.append((lag, hits / len(a)))
    return out


def recover_key(cipher: bytes, period: int) -> bytes:
    """Step 6: column-wise mode. Assumes the most common plaintext byte in each
    column is 0x00, which holds for DEX data sections."""
    key = bytearray(period)
    for i in range(period):
        col = cipher[i::period]
        key[i] = max(set(col), key=col.count)
    return bytes(key)


def offline_recover(apk: Path, outdir: Path) -> tuple[list, dict]:
    """Return (validated dex blobs, diagnostics). Implements article Steps 3,5,6,7."""
    diag: dict = {}
    with zipfile.ZipFile(apk) as z:
        shell = z.read("classes.dex")

    data_off, = struct.unpack_from("<I", shell, 0x6C)
    data_size, = struct.unpack_from("<I", shell, 0x68)
    payload = shell[data_off + data_size:]
    diag["payload_bytes"] = len(payload)
    diag["trailing_u32"] = struct.unpack_from("<I", payload, len(payload) - 4)[0] \
        if len(payload) >= 4 else None
    ok(f"appended payload = {len(payload):,} B "
       f"(trailing u32 = {diag['trailing_u32']}, observed 4 = blob count)")

    # -- Step 5: find the period
    #
    # A repeating-key XOR of period P spikes at EVERY multiple of P, not just at
    # P -- so "the peak is the largest value" is the wrong test and would reject
    # a correct recovery. The real signature is a comb: all elevated lags are
    # integer multiples of one fundamental P, and every other lag sits at the
    # 1/256 noise floor. EXP-0002 measured exactly that comb on this payload --
    # 50.85% at lag 64 decaying to 48.04% at 512, noise floor 1.85%.
    ac = autocorrelation(payload)
    if not ac:
        fail("payload too short to autocorrelate")
        return [], diag
    peak_lag, peak_score = max(ac, key=lambda t: t[1])
    ok(f"autocorrelation peak {peak_score * 100:.2f}% at lag {peak_lag}")
    if peak_score < 0.30:
        fail(f"no XOR periodicity (peak {peak_score * 100:.2f}% < 30%) -- "
             "this payload is not a repeating-key XOR; use --device")
        return [], diag

    elevated = [lag for lag, v in ac if v >= 0.40 * peak_score]
    period = min(elevated)                     # fundamental period
    harmonic = [l for l in elevated if l % period == 0]
    offcomb = [(l, v) for l, v in ac if l % period != 0]
    noise_max = max((v for _, v in offcomb), default=0.0)
    diag["period"] = period
    diag["autocorr_peak"] = {
        "peak_lag": peak_lag, "peak": peak_score, "period": period,
        "harmonics": harmonic, "noise_floor_max": noise_max,
    }
    ok(f"  fundamental period {period} "
       f"({len(harmonic)} harmonic lags: {harmonic[:8]}"
       f"{'...' if len(harmonic) > 8 else ''})")
    ok(f"  off-comb noise floor {noise_max * 100:.2f}% "
       f"(EXP-0002 observed 1.85%)")

    # The comb must actually be a comb: every elevated lag a multiple of period.
    stragglers = [l for l in elevated if l % period != 0]
    if stragglers:
        fail(f"autocorrelation is not periodic: elevated lags {stragglers} are "
             f"not multiples of {period}. Not a simple repeating-key XOR; use --device")
        return [], diag
    if noise_max > 0.5 * peak_score:
        fail(f"noise floor {noise_max * 100:.2f}% is too close to the peak "
             f"{peak_score * 100:.2f}% to claim a period; use --device")
        return [], diag

    # -- Step 6: key by column mode, then PROVE with checksums
    key = recover_key(payload, period)
    diag["key_hex"] = key.hex()
    plain = bytes(b ^ key[i % period] for i, b in enumerate(payload))
    first = validate_dex(plain)
    ok(f"key = {key.hex()}")
    ok(f"first blob: magic={first.magic!r} file_size={first.file_size:,} "
       f"adler32={first.adler32_ok} sha1={first.sha1_ok} -> {first.why}")
    if not first.valid:
        fail("column-mode key did not produce a checksum-valid dex. "
             "The blob's plaintext is not zero-dominated (EXP-0002 saw exactly "
             "this on the secondary blob). Use --device.")
        return [], diag

    # -- Step 7: split on each blob's OWN file_size field, never a fixed stride.
    # validate_dex(trim=True) slices to file_size before checksumming, so a blob
    # followed by the next one still validates.
    blobs: list[bytes] = []
    pos = 0
    while pos < len(plain):
        cand = validate_dex(plain[pos:])
        if not cand.valid:
            break
        blobs.append(cand.data)
        ok(f"blob {len(blobs)}: {cand.file_size:,} B  class_defs={cand.class_defs} "
           f"sha256={cand.sha256[:16]}...")
        pos += cand.file_size
    diag["offline_blob_count"] = len(blobs)
    diag["offline_blob_bytes"] = sum(len(b) for b in blobs)
    diag["offline_unconsumed"] = len(plain) - pos
    if pos < len(plain):
        warn(f"{len(plain) - pos:,} B of decrypted payload left over after the "
             f"last valid dex. Expected: the trailing u32 blob count plus any "
             f"blob whose key differs (EXP-0002). Not a failure of the method.")

    res = [validate_dex(b) for b in blobs]
    for i, r in enumerate(res):
        (outdir / f"offline_blob{i + 1}.dex").write_bytes(r.data)
    return res, diag


# ==========================================================================
# device path -- Step 1 (T-0021 then T-0010)
# ==========================================================================
def sh(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["adb"] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def device_recover(apk: Path, serial: str | None, outdir: Path,
                   gate: Gate) -> tuple[list, dict]:
    """T-0021 storage-model detection, then T-0010 anon-DEX carving."""
    diag: dict = {}
    adb = require_tool("adb")

    devs = subprocess.run([adb, "devices"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout
    online = [l.split()[0] for l in devs.splitlines()[1:]
              if l.strip() and l.strip().endswith("device")]
    if serial is None:
        if not online:
            fail("no device in 'device' state -- T-0010 needs a live rooted device")
            raise SystemExit(EXIT_ENVIRONMENT)
        serial = online[0]
    ok(f"device {serial}")

    # Root is checked FIRST: without it every later probe (data-dir file count,
    # /proc/<pid>/maps, /proc/<pid>/mem) fails at once, and reporting a
    # package-resolution error instead would point at the wrong problem.
    probe = subprocess.run([adb, "-s", serial, "shell", "su -c id"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
    if "uid=0" not in probe.stdout:
        fail(f"device {serial} is not rooted (`su -c id` -> "
             f"{(probe.stdout or probe.stderr).strip()[:120] or 'no output'}). "
             "T-0010 needs root to read /proc/<pid>/maps and /proc/<pid>/mem.")
        raise SystemExit(EXIT_ENVIRONMENT)
    ok("root confirmed (uid=0)")

    man = subprocess.run([adb, "-s", serial, "shell", "pm", "list", "packages"],
                         capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    pkg = None
    for cand in _guess_packages(apk):
        if cand in man:
            pkg = cand
            break
    if not pkg:
        fail(f"the app is not installed on {serial}. Candidates tried: "
             f"{_guess_packages(apk)}. Install it first, or pass --pkg.")
        raise SystemExit(EXIT_ENVIRONMENT)
    ok(f"package {pkg}")
    diag["package"] = pkg

    # ---- T-0021: diff the data-dir file count across a launch -------------
    def filecount() -> int:
        """Files under /data/data/<pkg>. Raises on a FAILED probe.

        A failed probe must never be representable as a number, because the
        routing decision is `before == after` -> "memory-resident". If su is
        missing both probes return the same error value and the comparison
        silently reports "nothing changed", which is the wrong answer and would
        route a disk-harvestable packer into memory carving.
        """
        p = subprocess.run(
            [adb, "-s", serial, "shell", f"su -c 'find /data/data/{pkg} -type f | wc -l'"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        lines = [l.strip() for l in p.stdout.strip().splitlines() if l.strip()]
        if not lines or not lines[-1].isdigit():
            detail = (p.stderr or p.stdout or "").strip()[:200] or "empty output"
            raise RuntimeError(
                f"cannot read /data/data/{pkg} (root probe failed: {detail}). "
                "T-0021 needs a rooted device; refusing to guess the storage "
                "model from a failed probe.")
        return int(lines[-1])

    # (root was already verified up front, before package resolution)
    subprocess.run([adb, "-s", serial, "shell", f"am force-stop {pkg}"],
                   capture_output=True, text=True)
    try:
        before = filecount()
    except RuntimeError as e:
        fail(str(e))
        raise SystemExit(EXIT_ENVIRONMENT)
    ok(f"T-0021 baseline: {before} files in /data/data/{pkg}")

    subprocess.run([adb, "-s", serial, "logcat", "-c"], capture_output=True)
    main = _launch_activity(apk, pkg)
    subprocess.run([adb, "-s", serial, "shell", f"am start -n {pkg}/{main}"],
                   capture_output=True, text=True)
    import time
    time.sleep(12)
    try:
        after = filecount()
    except RuntimeError as e:
        fail(str(e))
        raise SystemExit(EXIT_ENVIRONMENT)
    ok(f"after launch: {after} files")
    diag["datadir_before"] = before
    diag["datadir_after"] = after
    diag["storage_model"] = "memory-resident" if after == before else "disk-harvestable"

    if after == before:
        ok("VERDICT memory-resident -> T-0010 anon-DEX carve "
           "(on-device file harvest T-0019 is a dead end)")
        gate.add("STRUCTURAL", "storage-model-detected", "PASS",
                 f"T-0021: /data/data file count {before} -> {after} (unchanged) "
                 f"=> InMemoryDexClassLoader, route to T-0010")
    else:
        warn(f"data dir GREW {before} -> {after}: this packer wrote dex to disk. "
             "T-0019 applies -- copy the unpack dir instead of carving memory. "
             "T-0010 not run.")
        gate.add("STRUCTURAL", "storage-model-detected", "COMMAND_SUCCESS",
                 f"/data/data grew {before} -> {after}; T-0019 applies, not T-0010")
        return [], diag

    # ---- T-0010: enumerate anon DEX regions, dd them, carve ---------------
    pid = subprocess.run([adb, "-s", serial, "shell", f"pidof {pkg}"],
                         capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout.strip().split()
    if not pid:
        fail(f"app {pkg} is not running after launch -- no payload in memory. "
             "The app may have crashed on the protected stub; check "
             "`adb logcat -b crash` before retrying.")
        gate.add("STRUCTURAL", "payload-resident", "FAIL",
                 f"pidof {pkg} returned no pid; the app did not stay alive "
                 "long enough to hold the decrypted dex in memory")
        return [], diag
    pid = pid[0]
    ok(f"pid {pid}")

    maps = subprocess.run([adb, "-s", serial, "shell", f"su -c 'cat /proc/{pid}/maps'"],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout
    if "dalvik-DEX" not in maps:
        fail("no [anon:dalvik-DEX data] regions in /proc/%s/maps. Without them "
             "there is no in-memory dex to carve -- the packer may have used a "
             "different loader, or the app died. Do not conclude success." % pid)
        gate.add("STRUCTURAL", "anon-dex-regions", "FAIL",
                 f"/proc/{pid}/maps contains no [anon:dalvik-DEX data] region; "
                 "T-0010's precondition is absent")
    regions = []
    for line in maps.splitlines():
        if "dalvik-DEX data" not in line:
            continue
        rng, perms = line.split()[0], line.split()[1]
        lo, hi = (int(x, 16) for x in rng.split("-"))
        if "r" in perms:
            regions.append((lo, hi - lo))
    ok(f"T-0010: {len(regions)} readable [anon:dalvik-DEX data] regions")
    diag["regions"] = [{"addr": hex(a), "size": s} for a, s in regions]

    for i, (addr, size) in enumerate(regions):
        remote = f"/data/local/tmp/ark_r{i}.bin"
        subprocess.run([adb, "-s", serial, "shell",
                        f"su -c 'dd if=/proc/{pid}/mem of={remote} bs=4096 "
                        f"iflag=skip_bytes,count_bytes skip={addr} count={size}'"],
                       capture_output=True, text=True)
        local = outdir / f"region{i + 1}.bin"
        subprocess.run([adb, "-s", serial, "pull", remote, str(local)],
                       capture_output=True, text=True)
        subprocess.run([adb, "-s", serial, "shell", f"rm -f {remote}"],
                       capture_output=True)

    res: list = []
    for i in range(len(regions)):
        blob = (outdir / f"region{i + 1}.bin")
        if not blob.exists():
            continue
        for r in carve_dex(blob.read_bytes()):
            r.data = r.data
            res.append(r)
            (outdir / f"device_blob{len(res)}.dex").write_bytes(r.data)
            ok(f"region {i + 1}: dex {r.file_size:,} B class_defs={r.class_defs} "
               f"sha256={r.sha256[:16]}... (adler32+sha1 match)")
    diag["device_blob_count"] = len(res)
    return res, diag


def _guess_packages(apk: Path) -> list[str]:
    """Best-effort package name. Binary manifest => fall back to the filename."""
    out = []
    try:
        import re
        aapt2 = find_tool("aapt2")
        if aapt2:
            p = subprocess.run([aapt2, "dump", "badging", str(apk)],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            m = re.search(r"package: name='([^']+)'", p.stdout)
            if m:
                out.append(m.group(1))
    except Exception:
        pass
    out.append(apk.stem)
    return out


def _launch_activity(apk: Path, pkg: str) -> str:
    aapt2 = find_tool("aapt2")
    if aapt2:
        p = subprocess.run([aapt2, "dump", "badging", str(apk)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        for line in p.stdout.splitlines():
            if "launchable-activity" in line:
                name = line.split("name=")[1].split(" ")[0].strip("'")
                return name.replace(pkg, "", 1) if name.startswith(pkg) else name
    return ".MainActivity"


# ==========================================================================
# rebuild
# ==========================================================================
def rebuild(apk: Path, dexes: list, out_apk: Path, work: Path,
            gate: Gate) -> None:
    """Assemble the unpacked APK. Handles the two traps the article records:
    delete the packer's manifest android:name, and keep the app's own .so."""
    java = find_java()
    apktool = REPO_APKTOOL
    if not java or not apktool.exists():
        warn("apktool/java missing -- skipping rebuild; dex are written separately")
        return
    step("R", "rebuild (apktool)")

    src = work / "decoded"
    run([java, "-jar", apktool, "d", "-f", "-s", "-o", src, apk])

    man = src / "AndroidManifest.xml"
    if man.exists():
        text = man.read_text(encoding="utf-8", errors="replace")
        import re
        new = re.sub(r'\s*android:name="[^"]*"', "", text, count=1) \
            if re.search(r'<application[^>]*android:name="', text) else text
        if new != text:
            man.write_text(new, encoding="utf-8")
            ok("removed the packer's <application android:name> "
               "(no recovered class extends Application)")

    for i, d in enumerate(dexes):
        target = src / ("classes.dex" if i == 0 else f"classes{i + 1}.dex")
        target.write_bytes(d.data)

    dropped, kept = [], []
    for so in (src / "lib").rglob("*.so") if (src / "lib").exists() else []:
        if so.name == STUB_SO:
            so.unlink(); dropped.append(so.name)
        else:
            kept.append(so.name)
    for a in (src / "assets").rglob("*") if (src / "assets").exists() else []:
        if a.is_file() and "jiagu" in a.name.lower():
            a.unlink(); dropped.append(a.name)
    ok(f"dropped packer files {dropped or '(none)'} | kept app libs {kept or '(none)'}")

    run([java, "-jar", apktool, "b", str(src), "-o", str(work / "unsigned.apk")])

    zipalign = find_tool("zipalign")
    if zipalign:
        run([zipalign, "-f", "-p", "4", str(work / "unsigned.apk"), str(out_apk)])
        ok(f"zipaligned -> {out_apk}")
    else:
        shutil_out = work / "aligned.apk"
        shutil_out.write_bytes((work / "unsigned.apk").read_bytes())
        out_apk.write_bytes(shutil_out.read_bytes())
        warn("zipalign missing -- copied unaligned")

    signer = find_tool("apksigner")
    ks = Path.home() / ".android" / "debug.keystore"
    if signer and ks.exists() and find_java():
        import os
        env = dict(os.environ, JAVA_HOME=str(Path(find_java()).parent.parent))
        p = subprocess.run([signer, "sign", "--ks", str(ks),
                            "--ks-pass", "pass:android", "--key-pass", "pass:android",
                            "--ks-key-alias", "androiddebugkey",
                            "--v1-signing-enabled", "true",
                            "--v2-signing-enabled", "true",
                            "--v3-signing-enabled", "true", str(out_apk)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env)
        ok("signed (v1/v2/v3) with the local debug keystore"
           if p.returncode == 0 else f"apksigner failed: {p.stderr[:200]}")
    else:
        warn("apksigner or debug.keystore missing -- APK left unsigned")
    gate.add("STRUCTURAL", "rebuild", "PASS",
             f"rebuilt {out_apk.name}: {len(dexes)} dex, dropped {dropped}, kept {kept}")


REPO_APKTOOL = Path(__file__).resolve().parents[2] / "tools" / "apktool.jar"


# ==========================================================================
# main
# ==========================================================================
@main_wrapper
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Unpack a Chiko/NeoArk (Art-Jiagu) APK")
    ap.add_argument("apk", type=Path)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true",
                      help="host-only XOR path; primary blob only")
    mode.add_argument("--device", action="store_true",
                      help="rooted device anon-DEX carve; recovers all blobs")
    ap.add_argument("--serial", help="adb serial (default: first online device)")
    ap.add_argument("--rebuild", action="store_true",
                    help="also assemble a signed <stem>-unpacked.apk next to the input")
    a = ap.parse_args(argv)

    apk = a.apk.resolve()
    if not apk.is_file():
        fail(f"not a file: {apk}")
        return EXIT_ENVIRONMENT

    step("0", "fingerprint gate (never run this method on an unidentified APK)")
    require_fingerprint(fingerprint(apk), apk)

    out_apk, dexdir = output_paths(apk)
    work = scratch()
    blobdir = work / "blobs"
    blobdir.mkdir(parents=True, exist_ok=True)
    _say(f"  input   : {apk}")
    _say(f"  deliver : {out_apk}")
    _say(f"  scratch : {work}")

    gate = Gate(work / "gate")
    use_device = a.device or (not a.offline and find_tool("adb") and _has_device())
    dexes: list = []

    if use_device:
        step("1", "device path -- T-0021 storage model, then T-0010 anon-DEX carve")
        try:
            dexes, diag = device_recover(apk, a.serial, blobdir, gate)
        except SystemExit as e:
            return e.code
    else:
        step("3-8", "offline path -- appended payload, period, key, split, classify")
        dexes, diag = offline_recover(apk, blobdir)
        _say(f"  diagnostics: {json.dumps({k: v for k, v in diag.items() if k != 'key_hex'})}")
        warn("offline path recovers the PRIMARY blob only. EXP-0002 proved the "
             "other blobs use different keys. Use --device for the whole app.")

    if not dexes:
        fail("no checksum-valid dex recovered -- method did not work on this APK")
        gate.add("PARSER", "dex-recovered", "FAIL", "zero checksum-valid dex")
        gate.run()
        return EXIT_FAILED

    # ---- PARSER: every blob must pass adler32 + sha1 --------------------
    for i, d in enumerate(dexes):
        gate.add("PARSER", f"dex{i + 1}-header", "PASS" if d.valid else "FAIL",
                 f"{d.file_size:,} B class_defs={d.class_defs} strings={d.string_ids} "
                 f"adler32={d.adler32_ok} sha1={d.sha1_ok} sha256={d.sha256[:16]}...")

    # ---- Step 8 / CONTENT: is this the APP, or just a helper component? ---
    # This must be a real assertion. A check that reports PASS while printing
    # "verify this yourself" is a rubber stamp, and it is how EXP-0002 came to
    # claim a successful unpack when it had only recovered framework dex.
    pkg = _manifest_app_class(apk)[1] or _package_from_zip(apk)
    app_dexes = []
    if pkg:
        for i, d in enumerate(dexes):
            n = defines_namespace(d, pkg)
            if n:
                app_dexes.append((i, n))
    total_app_types = sum(n for _, n in app_dexes)
    if not pkg:
        gate.add("CONTENT", "app-classes-present", "COMMAND_SUCCESS",
                 "could not resolve the app package from the manifest, so app "
                 "classes could not be confirmed. Unverified -- not learnable.")
    elif total_app_types:
        where = ", ".join(f"dex{i + 1}={n} types" for i, n in app_dexes)
        gate.add("CONTENT", "app-classes-present", "PASS",
                 f"app package {pkg} defined in recovered dex: {where} "
                 f"({total_app_types} type descriptors)")
        ok(f"app classes confirmed in {pkg} ({where})")
    else:
        gate.add("CONTENT", "app-classes-present", "FAIL",
                 f"NO recovered dex defines a class in the app package {pkg}. "
                 f"{len(dexes)} checksum-valid dex, "
                 f"{sum(d.class_defs for d in dexes):,} class_defs total, but all "
                 "of it is third-party framework code. The app's own logic is "
                 "NOT recovered -- this is a helper-component recovery, which is "
                 "the Step 8 failure mode, not an unpack.")
        fail(f"recovered dex contains no {pkg} classes -> the app is NOT unpacked")
        if not use_device:
            fail("re-run with --device (T-0010 anon-DEX carve) to get the real "
                 "app logic; EXP-0002 proved the offline key does not cover the "
                 "other blobs")

    # ---- REPRODUCIBILITY ------------------------------------------------
    h = hashlib.sha256()
    for d in dexes:
        h.update(d.sha256.encode())
    gate.add("REPRODUCIBILITY", "sha256-stable", "PASS",
             f"combined {h.hexdigest()} from {len(dexes)} dex hashes")

    # Only publish a deliverable once the app's own classes are actually in
    # hand. Writing a -unpacked.apk next to the input when the app logic was
    # never recovered is the failure this whole guard exists to prevent.
    if total_app_types:
        if a.rebuild:
            rebuild(apk, dexes, out_apk, work, gate)
            if out_apk.exists():
                gate.add("DOWNSTREAM", "artifact-written", "PASS",
                         f"{out_apk} ({out_apk.stat().st_size:,} B) "
                         f"sha256={hashlib.sha256(out_apk.read_bytes()).hexdigest()}")
        else:
            dexdir.mkdir(parents=True, exist_ok=True)
            for i, d in enumerate(dexes):
                (dexdir / ("classes.dex" if i == 0
                           else f"classes{i + 1}.dex")).write_bytes(d.data)
            ok(f"dex written to {dexdir} (pass --rebuild to also emit the APK)")
    else:
        for i, d in enumerate(dexes):
            (work / f"unconfirmed_blob{i + 1}.dex").write_bytes(d.data)
        _say(f"\n  no deliverable written. The recovered dex are framework-only "
             f"and were kept in scratch:\n    {work}")

    verdict, rc, _ = gate.run()
    if total_app_types:
        if verdict == "VERIFIED_SUCCESS":
            ok(f"VERIFIED_SUCCESS -- {len(dexes)} dex, app classes confirmed, "
               f"method validated on this APK")
            if not a.rebuild:
                _say("\n  next: rebuild + install, or re-run with --rebuild")
        else:
            warn(f"verdict {verdict} -- not learnable, do not record as a success")
    else:
        fail(f"NOT UNPACKED. Checksum-valid dex were recovered, but none contain "
             f"{pkg or 'the app package'} classes -- only framework/helper code. "
             f"Verdict: {verdict}. The fast path stopped here on purpose: "
             f"reporting this as a successful unpack is the Step 8 error.")
        if not use_device:
            fail("fix: re-run with --device on a rooted device "
                 "(T-0021 -> T-0010) to carve the real app dex out of memory")
    return rc


def _package_from_zip(apk: Path) -> str | None:
    """Best-effort package name, used only for the CONTENT assertion."""
    aapt2 = find_tool("aapt2")
    if not aapt2:
        return None
    import re
    p = subprocess.run([aapt2, "dump", "badging", str(apk)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    m = re.search(r"package: name='([^']+)'", p.stdout)
    return m.group(1) if m else None


def defines_namespace(d: DexResult, pkg: str) -> int:
    """Count type descriptors in the dex that belong to the app's own package.

    A dex type descriptor is `Lcom/mducdz/fakeping/MainActivity;`. Counting the
    `L<pkg>/` prefix tells us whether this blob carries the app's own classes or
    only third-party framework code. This is the check that separates "unpacked
    the app" from "recovered a helper component" -- the exact confusion Step 8 of
    the article exists to prevent, and the one EXP-0002 originally made.
    """
    if not d.data or not pkg:
        return 0
    needle = b"L" + pkg.replace(".", "/").encode() + b"/"
    return d.data.count(needle)


def _has_device() -> bool:
    adb = find_tool("adb")
    if not adb:
        return False
    out = subprocess.run([adb, "devices"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return any(l.strip().endswith("device") for l in out.splitlines()[1:])


if __name__ == "__main__":
    sys.exit(main())
