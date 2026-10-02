#!/usr/bin/env python3
"""
test_chiko_neoark.py — negative and positive tests for the Chiko fast path.

A fingerprint gate that has never been shown refusing something is an untested
gate. These tests build adversarial inputs, run the real script as a subprocess,
and assert the exit code.

    python scripts/packers/tests/test_chiko_neoark.py [--apk <real chiko apk>]

Exit 0 = all tests behaved as specified.

FIXTURES ARE SYNTHESIZED, NOT CHECKED IN. Four of the five are built here from
scratch, so this file stays a few KB instead of carrying multi-MB binaries, and
so nobody can accidentally commit a real APK. Only the positive test needs a
real sample, passed via --apk.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "chiko_neoark.py"
EXIT_OK, EXIT_FAILED, EXIT_COMMAND_SUCCESS = 0, 1, 10
EXIT_FINGERPRINT_MISMATCH, EXIT_ENVIRONMENT = 20, 30


# --------------------------------------------------------------------------
# fixture construction
# --------------------------------------------------------------------------
def _fix_adler(d: bytearray) -> None:
    struct.pack_into("<I", d, 0x20, len(d))
    struct.pack_into("<I", d, 0x08, zlib.adler32(bytes(d[12:])) & 0xFFFFFFFF)


def _minimal_dex() -> bytes:
    """A structurally plausible dex header with one class_def. Not a real dex:
    we only need the header fields the fingerprint reads."""
    d = bytearray(0x70)
    d[0:8] = b"dex\n035\x00"
    struct.pack_into("<I", d, 0x24, 0x70)          # header_size
    struct.pack_into("<I", d, 0x28, 0x12345678)   # endian
    struct.pack_into("<I", d, 0x38, 10)           # string_ids_size
    struct.pack_into("<I", d, 0x40, 4)            # type_ids_size
    struct.pack_into("<I", d, 0x60, 1)            # class_defs_size
    struct.pack_into("<I", d, 0x6C, 0x70)         # data_off
    struct.pack_into("<I", d, 0x68, 0)            # data_size
    _fix_adler(d)
    return bytes(d)


def make_clean_apk(out: Path) -> Path:
    """A normal, unpacked APK. No stub .so, no appended payload."""
    p = out / "neg_a_clean.apk"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("AndroidManifest.xml", b"\x00" * 16)
        z.writestr("classes.dex", _minimal_dex())
        z.writestr("lib/arm64-v8a/libfping.so", b"\x7fELF" + b"\x00" * 32)
    return p


def make_decoy_other_packer(out: Path) -> Path:
    """The dangerous near-miss: a 'jiagu' decoy asset AND an appended payload,
    but a different packer's .so. This is the shape that produced the original
    360-jiagu false positive. Weak indicators hit; strong ones must not."""
    p = out / "neg_b_decoy_other_packer.apk"
    d = bytearray(_minimal_dex())
    d += os.urandom(4096)
    _fix_adler(d)
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("AndroidManifest.xml", b"\x00" * 16)
        z.writestr("classes.dex", bytes(d))
        z.writestr("assets/libjiagu_mips.a", b"360 jiagu" * 11)   # 99 B decoy
        z.writestr("lib/arm64-v8a/libsomeotherpacker.so", b"\x7fELF" + b"\x00" * 16)
    return p


def make_chiko_lookalike_random(out: Path, stub: bytes | None) -> Path:
    """Chiko-shaped but the payload is random noise, not a periodic XOR.

    If we have the real libchikoStub.so the fingerprint PASSES, which is the
    point: the script must then refuse to invent a key from the autocorrelation
    rather than reporting a bogus recovery.
    """
    p = out / "neg_c_chiko_random_payload.apk"
    d = bytearray(_minimal_dex())
    d += os.urandom(1_500_000) + struct.pack("<I", 4)
    _fix_adler(d)
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("AndroidManifest.xml", b"\x00" * 16)
        z.writestr("classes.dex", bytes(d))
        if stub:
            z.writestr("lib/arm64-v8a/libchikoStub.so", stub)
        else:
            # fabricate a stub carrying the loader strings so the strong
            # indicator still passes without shipping a real binary
            z.writestr("lib/arm64-v8a/libchikoStub.so",
                       b"\x7fELF" + b"\x00ark_payload_%d.dex\x00com/ark/safe/StubApp\x00")
    return p


def make_not_a_zip(out: Path) -> Path:
    p = out / "neg_d_not_a_zip.bin"
    p.write_bytes(b"this is definitely not a zip archive" * 40)
    return p


# --------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------
def run(apk: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(SCRIPT), str(apk), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=1800)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", type=Path, help="a real Chiko/NeoArk APK (positive test)")
    a = ap.parse_args()

    if not SCRIPT.exists():
        print(f"FATAL: {SCRIPT} not found")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="packer-tests-"))
    results: list[tuple[str, int, int, str]] = []

    def check(name: str, fixture: Path, want: int, *args: str) -> None:
        code, out = run(fixture, *args)
        ok = code == want
        results.append((name, code, want, "PASS" if ok else "FAIL"))
        print(f"[{'ok  ' if ok else 'FAIL'}] {name}: exit {code} (want {want})")
        if not ok:
            for line in out.strip().splitlines()[-14:]:
                print("        " + line)

    print(f"fixtures: {tmp}\n")

    check("clean unpacked APK is refused",
          make_clean_apk(tmp), EXIT_FINGERPRINT_MISMATCH, "--offline")
    check("jiagu decoy + other packer is refused",
          make_decoy_other_packer(tmp), EXIT_FINGERPRINT_MISMATCH, "--offline")
    check("non-zip input fails cleanly",
          make_not_a_zip(tmp), EXIT_FINGERPRINT_MISMATCH, "--offline")
    check("missing file fails cleanly",
          tmp / "does_not_exist.apk", EXIT_ENVIRONMENT, "--offline")
    check("chiko shape + random payload is rejected, not guessed",
          make_chiko_lookalike_random(tmp, None), EXIT_FAILED, "--offline")

    if a.apk and a.apk.is_file():
        code, out = run(a.apk, "--offline")
        # The offline path on a real Chiko APK recovers only the framework blob,
        # which contains none of the app's classes, so it MUST NOT exit 0.
        want = EXIT_COMMAND_SUCCESS
        ok = code == want
        results.append(("real APK offline does not claim a full unpack",
                        code, want, "PASS" if ok else "FAIL"))
        print(f"[{'ok  ' if ok else 'FAIL'}] real APK offline: exit {code} "
              f"(want {want}, not 0)")
        if "VERIFIED_SUCCESS" in out and code == 0:
            print("        WARNING: reported VERIFIED_SUCCESS without app classes")
    else:
        print("[skip] real APK offline test (pass --apk <chiko.apk>)")

    failed = [r for r in results if r[3] != "PASS"]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    print(f"scratch kept for inspection: {tmp}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
