"""
_base.py — shared machinery for per-packer fast-path unpackers.

WHY THIS EXISTS
---------------
A packer article in `knowledge_base/wiki/packers/` is *knowledge*. It is prose an
agent has to re-derive commands from every time, which is slow. A script here is
the *speed*: one command that fingerprints, applies the documented method,
verifies, and emits.

RULES THIS MODULE ENFORCES (do not bypass them in a packer script):

1. FINGERPRINT GATE. A packer script must never run its method on an APK it
   did not positively identify. `require_fingerprint()` exits non-zero on a
   mismatch rather than guessing. This is what stops a Chiko method from being
   silently applied to a 360 jiagu APK.

2. VERIFICATION GATE. Nothing is reported as a success unless
   `verify_result.py gate` returns VERIFIED_SUCCESS: >=3 distinct categories
   with zero FAIL. `COMMAND_SUCCESS` is NOT learnable (see .kb/core-rules.md)
   and must exit non-zero here too.

3. OUTPUT LOCATION. The deliverable is written NEXT TO the input APK, named
   `<input-stem>-unpacked.apk`. Scratch goes to a temp dir. The packed input is
   read-only.

4. VERBATIM. Constants carry the observed values from the source experiment.
   Do not "clean up" a magic number -- if a value changes, that is new
   evidence and belongs in a new experiment, not a silent edit here.

Exit codes (shared by every packer script):
    0   VERIFIED_SUCCESS   >=3 gate categories, zero FAIL
    10  COMMAND_SUCCESS    something ran, but not enough to learn from
    20  FINGERPRINT_MISMATCH  the APK is not this packer -- do not proceed
    30  ENVIRONMENT       missing tool / no device / no root
    1   FAILED            the method ran and did not work
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from zipfile import BadZipFile

# --------------------------------------------------------------------------
# exit codes
# --------------------------------------------------------------------------
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_COMMAND_SUCCESS = 10
EXIT_FINGERPRINT_MISMATCH = 20
EXIT_ENVIRONMENT = 30

# --------------------------------------------------------------------------
# repo layout
# --------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
KB_ROOT = REPO_ROOT / "knowledge_base"
WIKI = KB_ROOT / "wiki"
SCRIPTS = REPO_ROOT / ".kb" / "scripts"
VERIFY_RESULT = SCRIPTS / "verify_result.py"


def _say(msg: str) -> None:
    print(msg, flush=True)


def step(n: int | str, title: str) -> None:
    _say(f"\n=== [{n}] {title} " + "=" * max(0, 58 - len(title)))


def ok(msg: str) -> None:
    _say(f"  [ok]   {msg}")


def warn(msg: str) -> None:
    _say(f"  [warn] {msg}")


def fail(msg: str) -> None:
    _say(f"  [FAIL] {msg}")


# --------------------------------------------------------------------------
# DEX validation -- the thing that makes a recovery trustworthy
# --------------------------------------------------------------------------
# A blob is only accepted when ART's OWN integrity fields agree. Raw address
# space or an XOR guess can look like a dex header; adler32+sha1 cannot lie
# without the blob being byte-exact. This is why the KB calls both mandatory.

DEX_MAGIC = b"dex\n"
DEX_ENDIAN = 0x12345678
DEX_HEADER_SIZE = 112


@dataclass
class DexResult:
    """Verdict on one candidate dex blob."""

    valid: bool
    data: bytes | None = None
    magic: str = ""
    file_size: int = 0
    header_size: int = 0
    endian: int = 0
    class_defs: int = 0
    string_ids: int = 0
    type_ids: int = 0
    adler32_ok: bool = False
    sha1_ok: bool = False
    sha256: str = ""
    why: str = ""

    @property
    def sha1_and_adler(self) -> bool:
        return self.adler32_ok and self.sha1_ok


def validate_dex(blob: bytes, trim: bool = True) -> DexResult:
    """Validate a candidate dex. Both adler32 and sha1 must match to pass.

    Offsets are from the DEX header spec:
        0x08  adler32  (checksum of bytes[12:])
        0x0c  sha1     (signature of bytes[32:])
        0x20  file_size
        0x24  header_size (0x70)
        0x28  endian_tag
        0x38  string_ids_size
        0x40  type_ids_size
        0x60  class_defs_size

    trim=True auto-slices the blob down to its own file_size first. That is
    required when unpacking a concatenated stream, where a blob is followed by
    the next one. Trimming cannot manufacture a false pass: adler32 and sha1
    are then computed over the trimmed bytes, so a wrong length still fails.
    """
    if len(blob) < DEX_HEADER_SIZE:
        return DexResult(False, why=f"too short ({len(blob)} B < {DEX_HEADER_SIZE})")
    if not blob.startswith(DEX_MAGIC):
        return DexResult(False, magic=repr(blob[:8]), why="no dex\\n magic")

    stored_adler, = struct.unpack_from("<I", blob, 0x08)
    file_size, = struct.unpack_from("<I", blob, 0x20)
    header_size, = struct.unpack_from("<I", blob, 0x24)
    endian, = struct.unpack_from("<I", blob, 0x28)
    string_ids, = struct.unpack_from("<I", blob, 0x38)
    type_ids, = struct.unpack_from("<I", blob, 0x40)
    class_defs, = struct.unpack_from("<I", blob, 0x60)

    if header_size != DEX_HEADER_SIZE:
        return DexResult(False, magic=blob[:8].decode("latin-1"),
                         why=f"header_size {header_size} != {DEX_HEADER_SIZE}")
    if endian != DEX_ENDIAN:
        return DexResult(False, magic=blob[:8].decode("latin-1"),
                         why=f"endian {endian:#x} != {DEX_ENDIAN:#x}")
    if file_size < DEX_HEADER_SIZE:
        return DexResult(False, magic=blob[:8].decode("latin-1"),
                         file_size=file_size,
                         why=f"file_size {file_size} < header {DEX_HEADER_SIZE}")
    if trim and len(blob) > file_size:
        blob = blob[:file_size]

    r = DexResult(
        valid=False,
        magic=blob[:8].decode("latin-1"),
        file_size=file_size,
        header_size=header_size,
        endian=endian,
        class_defs=class_defs,
        string_ids=string_ids,
        type_ids=type_ids,
    )
    if file_size != len(blob):
        r.why = f"file_size {file_size} != blob length {len(blob)}"
        return r

    r.adler32_ok = (zlib.adler32(blob[12:]) & 0xFFFFFFFF) == stored_adler
    r.sha1_ok = hashlib.sha1(blob[32:]).digest() == blob[12:32]
    r.sha256 = hashlib.sha256(blob).hexdigest()
    if r.adler32_ok and r.sha1_ok:
        r.valid = True
        r.data = blob
        r.why = "adler32 + sha1 both match"
    elif not r.adler32_ok and not r.sha1_ok:
        r.why = "adler32 AND sha1 both mismatch (wrong key or truncated)"
    else:
        r.why = "adler32/sha1 partial mismatch (truncated or misaligned)"
    return r


def carve_dex(buf: bytes) -> list[DexResult]:
    """Find every dex magic in a buffer and validate each candidate."""
    out: list[DexResult] = []
    pos = 0
    while True:
        i = buf.find(DEX_MAGIC, pos)
        if i < 0:
            break
        r = validate_dex(buf[i:])
        if r.valid:
            r.data = buf[i:i + r.file_size]
            out.append(r)
        pos = i + 1
    return out


# --------------------------------------------------------------------------
# fingerprint gate
# --------------------------------------------------------------------------
@dataclass
class Fingerprint:
    """Scored identification of a packer. `strong` checks must all pass."""

    name: str
    strong: list[tuple[str, bool, str]] = field(default_factory=list)
    weak: list[tuple[str, bool, str]] = field(default_factory=list)

    @property
    def strong_ok(self) -> bool:
        return bool(self.strong) and all(c[1] for c in self.strong)

    @property
    def score(self) -> int:
        return sum(1 for _, hit, _ in self.weak if hit)

    def report(self) -> str:
        lines = [f"  packer: {self.name}"]
        for label, hit, detail in self.strong:
            lines.append(f"  [STRONG {'HIT ' if hit else 'MISS'}] {label}"
                         + (f"  ({detail})" if detail else ""))
        for label, hit, detail in self.weak:
            lines.append(f"  [weak   {'HIT ' if hit else 'miss'}] {label}"
                         + (f"  ({detail})" if detail else ""))
        return "\n".join(lines)


def require_fingerprint(fp: Fingerprint, apk: Path) -> None:
    """Exit non-zero unless every STRONG indicator hit. Never guess."""
    _say(fp.report())
    if not fp.strong_ok:
        missed = [c[0] for c in fp.strong if not c[1]]
        fail(f"fingerprint MISMATCH for {apk.name}: no match on {missed}")
        fail("This script implements ONE packer's method. Refusing to run it on "
             "an APK it did not identify -- applying the wrong method silently "
             "is worse than not running.")
        _say("\nUse `python .kb/scripts/apk_fingerprint.py <apk>` to identify the "
             "packer, then pick the matching script from scripts/packers/.")
        sys.exit(EXIT_FINGERPRINT_MISMATCH)
    ok(f"fingerprint confirmed: {fp.name} (strong {sum(1 for c in fp.strong if c[1])}"
       f"/{len(fp.strong)}, weak {fp.score}/{len(fp.weak)})")


# --------------------------------------------------------------------------
# verification gate
# --------------------------------------------------------------------------
class Gate:
    """Collect category checks, then run the KB's own gate over them."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.checks: list[dict] = []

    def add(self, category: str, check: str, status: str, details: str, **extra) -> dict:
        rec = {"category": category, "check": check, "status": status,
               "details": details, "timestamp": "1970-01-01T00:00:00"}
        rec.update(extra)
        self.checks.append(rec)
        tag = {"PASS": "[ok]", "FAIL": "[FAIL]", "COMMAND_SUCCESS": "[warn]"}.get(status, "[?]")
        _say(f"  {tag} {category}/{check}: {details}")
        return rec

    def run(self) -> tuple[str, int, dict]:
        """Write the JSONs, call verify_result.py gate, return (verdict, rc, out)."""
        if not VERIFY_RESULT.exists():
            warn(f"{VERIFY_RESULT} missing -- cannot gate")
            return "UNGATED", EXIT_ENVIRONMENT, {}
        paths = []
        for i, c in enumerate(self.checks):
            p = self.workdir / f"check{i:02d}.json"
            p.write_text(json.dumps(c, indent=2), encoding="utf-8")
            paths.append(str(p))
        proc = subprocess.run(
            [sys.executable, str(VERIFY_RESULT), "gate", *paths],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        out = proc.stdout.strip()
        _say("\n--- gate ---")
        _say(out)
        verdict = "UNKNOWN"
        try:
            verdict = json.loads(out).get("verdict", "UNKNOWN")
        except Exception:
            pass
        if verdict == "VERIFIED_SUCCESS":
            return verdict, EXIT_OK, json.loads(out)
        if verdict == "COMMAND_SUCCESS":
            return verdict, EXIT_COMMAND_SUCCESS, {}
        return verdict, EXIT_FAILED, {}


# --------------------------------------------------------------------------
# output location -- deliverable goes next to the input
# --------------------------------------------------------------------------
def output_paths(apk: Path) -> tuple[Path, Path]:
    """(unpacked_apk, dex_dir) beside the packed input. Input stays read-only."""
    d = apk.resolve().parent
    return (d / f"{apk.stem}-unpacked.apk", d / f"{apk.stem}-unpacked-dex")


def scratch() -> Path:
    return Path(tempfile.mkdtemp(prefix="unpack-"))


# --------------------------------------------------------------------------
# tool discovery
# --------------------------------------------------------------------------
def find_tool(name: str) -> str | None:
    """Locate a host tool.

    `tool_discover.py` reports adb/aapt/apksigner/zipalign as available even
    when they are not on PATH, so an explicit PATH check plus the standard
    Android SDK locations is required here.
    """
    found = shutil.which(name)
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        cands = []
        if name == "adb":
            cands = [Path(local) / "Android/Sdk/platform-tools/adb.exe",
                     Path(local) / "Android/Sdk/platform-tools/adb"]
        else:
            cands = [Path(local) / f"Android/Sdk/build-tools/{v}/{name}.exe"
                     for v in ("35.0.0", "34.0.0", "33.0.0")]
            cands += [Path(local) / f"Android/Sdk/build-tools/{v}/{name}"
                      for v in ("35.0.0", "34.0.0", "33.0.0")]
        for c in cands:
            if c.exists():
                return str(c)
    return None


def require_tool(name: str) -> str:
    t = find_tool(name)
    if not t:
        fail(f"required tool not found: {name} (not on PATH, not in the SDK)")
        sys.exit(EXIT_ENVIRONMENT)
    return t


def find_java() -> str | None:
    j = shutil.which("java")
    if j:
        return j
    for base in (Path("C:/Program Files/Eclipse Adoptium"),
                 Path("C:/Program Files/Java")):
        if base.exists():
            for d in sorted(base.glob("*/bin/java.exe"), reverse=True):
                return str(d)
    return None


def run(cmd: list[str], *, timeout: int = 600, check: bool = False) -> subprocess.CompletedProcess:
    """Run a command, echoing it. Windows-safe (no shell string interpolation)."""
    _say(f"  $ {' '.join(str(c) for c in cmd)}")
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    if p.returncode != 0 and not check:
        fail(f"exit {p.returncode}")
        if p.stderr.strip():
            _say("  stderr: " + p.stderr.strip()[:500])
    return p


# --------------------------------------------------------------------------
# entrypoint decorator
# --------------------------------------------------------------------------
def main_wrapper(fn):
    """Turn an uncaught path/IO error into ENVIRONMENT rather than a traceback."""
    def inner(*a, **kw):
        try:
            return fn(*a, **kw)
        except KeyboardInterrupt:
            _say("\ninterrupted")
            return EXIT_FAILED
        except FileNotFoundError as e:
            fail(f"missing file: {e}")
            return EXIT_ENVIRONMENT
        except PermissionError as e:
            fail(f"permission denied: {e}")
            return EXIT_ENVIRONMENT
        except BadZipFile as e:
            fail(f"not a valid zip/APK: {e}")
            return EXIT_FINGERPRINT_MISMATCH
    return inner
