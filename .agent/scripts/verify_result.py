#!/usr/bin/env python3
"""
Verification gate — Phase 3 of the research loop
(see .kb/experiment-protocol.md section 3).

COMMAND_SUCCESS (exit 0 / file exists) is NOT evidence. A result is only
VERIFIED_SUCCESS when >= 3 distinct verification categories PASS and none FAIL:

    STRUCTURAL | PARSER | CONTENT | DOWNSTREAM | REPRODUCIBILITY

Every check emits one JSON object:
    {"category": ..., "check": ..., "status": "PASS"|"FAIL", "details": ...}

Subcommands:
    structural  --file X [--kind zip|dex|so|dir|file]
    parser      --dex X | --xml X | --json X
    content     --file X [--entry NAME] [--class com.foo.Bar] [--string needle]
    downstream  --tool apktool|jadx|apksigner|zipalign --file X
    reproducibility --file X [--expected-sha HEX] | --cmd "shell" --produces F [--expected-sha HEX]
    gate        RESULT.json [RESULT2.json ...]      # aggregate -> verdict

Exit codes: check -> 0 PASS, 1 FAIL, 4 error;
            gate   -> 0 VERIFIED_SUCCESS, 10 COMMAND_SUCCESS, 1 FAILED, 4 error.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tool_discover  # noqa: E402

CFG = json.loads((Path(__file__).resolve().parent / "tools.config.json").read_text(encoding="utf-8"))
BY_KEY = {t["key"]: t for t in CFG["tools"]}


def emit(category, check, status, details, extra=None) -> int:
    rec = {"category": category, "check": check, "status": status,
           "details": str(details)[:600], "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if extra:
        rec.update(extra)
    print(json.dumps(rec, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def run(cmd, timeout=300):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", shell=(os.name == "nt" and isinstance(cmd, str)))
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:
        return 125, str(e)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------- categories ---
def check_structural(args) -> int:
    f = Path(args.file)
    if not f.exists():
        return emit("STRUCTURAL", f"exists:{f.name}", "FAIL", "file missing")
    size = f.stat().st_size
    if size < 64:
        return emit("STRUCTURAL", f"size:{f.name}", "FAIL", f"only {size} bytes")
    kind = args.kind
    if kind is None:
        kind = "zip" if f.suffix.lower() == ".apk" or zipfile.is_zipfile(f) else "file"
    if kind == "zip":
        try:
            with zipfile.ZipFile(f) as z:
                bad = z.testzip()
                n = len(z.namelist())
            if bad:
                return emit("STRUCTURAL", "zip-crc", "FAIL", f"CRC failure at {bad}")
            if n == 0:
                return emit("STRUCTURAL", "zip-entries", "FAIL", "0 entries")
            return emit("STRUCTURAL", "zip-crc", "PASS", f"{n} entries, CRC ok, {size} bytes",
                        {"entries": n, "size": size})
        except Exception as e:
            return emit("STRUCTURAL", "zip-parse", "FAIL", str(e))
    if kind == "dex":
        magic = f.read_bytes()[:4]
        if magic != b"dex\n":
            return emit("STRUCTURAL", "dex-magic", "FAIL", f"magic={magic!r}")
        return emit("STRUCTURAL", "dex-magic", "PASS", f"dex magic ok, {size} bytes")
    if kind == "so":
        magic = f.read_bytes()[:4]
        if magic != b"\x7fELF":
            return emit("STRUCTURAL", "elf-magic", "FAIL", f"magic={magic!r}")
        return emit("STRUCTURAL", "elf-magic", "PASS", "ELF header ok")
    if kind == "dir":
        n = sum(1 for _ in f.rglob("*"))
        return emit("STRUCTURAL", "dir-populated", "PASS" if n > 2 else "FAIL", f"{n} entries")
    return emit("STRUCTURAL", f"file:{f.name}", "PASS", f"{size} bytes present")


def check_parser(args) -> int:
    if args.dex:
        f = Path(args.dex)
        data = f.read_bytes()
        if data[:4] != b"dex\n":
            return emit("PARSER", "dex-magic", "FAIL", f"magic={data[:4]!r}")
        file_size = struct.unpack_from("<I", data, 32)[0]
        if file_size != len(data):
            return emit("PARSER", "dex-file-size", "FAIL", f"header {file_size} != actual {len(data)}")
        import zlib
        stored = struct.unpack_from("<I", data, 8)[0]
        calc = zlib.adler32(data[12:]) & 0xFFFFFFFF
        if stored != calc:
            return emit("PARSER", "dex-adler32", "FAIL", f"stored {stored:#x} != calc {calc:#x}")
        import hashlib as hl
        stored_sha = data[12:32]
        calc_sha = hl.sha1(data[32:]).digest()
        if stored_sha != calc_sha:
            return emit("PARSER", "dex-sha1", "FAIL", "header sha1 mismatch")
        string_ids = struct.unpack_from("<I", data, 56)[0]
        type_ids = struct.unpack_from("<I", data, 64)[0]
        if string_ids == 0:
            return emit("PARSER", "dex-string-ids", "FAIL", "0 strings")
        return emit("PARSER", "dex-header", "PASS",
                    f"magic/size/adler32/sha1 ok; {string_ids} strings, {type_ids} types",
                    {"string_ids": string_ids, "type_ids": type_ids})
    if args.xml:
        f = Path(args.xml)
        try:
            import xml.etree.ElementTree as ET
            ET.parse(f)
            return emit("PARSER", "xml-wellformed", "PASS", "XML parses")
        except Exception as e:
            return emit("PARSER", "xml-wellformed", "FAIL", str(e))
    if args.json:
        f = Path(args.json)
        try:
            json.loads(f.read_text(encoding="utf-8"))
            return emit("PARSER", "json-valid", "PASS", "JSON parses")
        except Exception as e:
            return emit("PARSER", "json-valid", "FAIL", str(e))
    return emit("PARSER", "parser", "FAIL", "no input given (--dex/--xml/--json)")


def dex_streams(path: Path):
    """Yield raw bytes of every classes*.dex inside an apk/zip, or the file itself."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for n in sorted(z.namelist()):
                if re.fullmatch(r"classes\d*\.dex", n):
                    yield n, z.read(n)
    else:
        yield path.name, path.read_bytes()


def check_content(args) -> int:
    f = Path(args.file)
    if not f.exists():
        return emit("CONTENT", "file-exists", "FAIL", "file missing")
    if args.entry:
        try:
            with zipfile.ZipFile(f) as z:
                names = z.namelist()
            ok = args.entry in names
            return emit("CONTENT", f"entry:{args.entry}", "PASS" if ok else "FAIL",
                        "present" if ok else f"absent (have {len(names)} entries)")
        except Exception as e:
            return emit("CONTENT", "zip-read", "FAIL", str(e))
    if args.cls:
        needle = ("L" + args.cls.replace(".", "/") + ";").encode()
        hits = [n for n, data in dex_streams(f) if needle in data]
        return emit("CONTENT", f"class:{args.cls}", "PASS" if hits else "FAIL",
                    f"found in {hits}" if hits else "descriptor not in any dex")
    if args.string:
        needle = args.string.encode("utf-8", errors="ignore")
        hits = [n for n, data in dex_streams(f) if needle in data]
        return emit("CONTENT", f"string:{args.string}", "PASS" if hits else "FAIL",
                    f"found in {hits}" if hits else "string not in any dex")
    return emit("CONTENT", "content", "FAIL", "no --entry/--class/--string given")


def check_downstream(args) -> int:
    f = Path(args.file)
    tool = args.tool
    if tool == "zipalign":
        exe = tool_discover.resolve_path(BY_KEY["zipalign"]["search"])
        if not exe:
            return emit("DOWNSTREAM", "zipalign-present", "FAIL", "zipalign not found")
        rc, out = run([exe, "-c", "-p", "4", str(f)])
        return emit("DOWNSTREAM", "zipalign -c -p 4", "PASS" if rc == 0 else "FAIL",
                    out[:300] or f"exit {rc}")
    if tool == "apksigner":
        exe = tool_discover.resolve_path(BY_KEY["apksigner"]["search"])
        if not exe:
            return emit("DOWNSTREAM", "apksigner-present", "FAIL", "apksigner not found")
        rc, out = run([exe, "verify", "-v", str(f)])
        return emit("DOWNSTREAM", "apksigner verify", "PASS" if rc == 0 else "FAIL",
                    (out[:300] or f"exit {rc}"))
    if tool in ("apktool", "jadx"):
        java = tool_discover.find_java()
        if tool == "apktool":
            jar = tool_discover.resolve_path(BY_KEY["apktool"]["search"])
            if not (java and jar):
                return emit("DOWNSTREAM", "apktool-present", "FAIL", "apktool/java missing")
            cmd = [java, "-jar", jar, "d", "-f", str(f)]
        else:
            exe = tool_discover.resolve_path(BY_KEY["jadx"]["search"])
            if not exe:
                return emit("DOWNSTREAM", "jadx-present", "FAIL", "jadx not found")
            cmd = [exe]
        tmp = Path(tempfile.mkdtemp(prefix="verify_"))
        outdir = tmp / "out"
        cmd += ["-o", str(outdir)] if tool == "apktool" else ["-d", str(outdir), str(f)]
        if tool == "apktool":
            cmd.append(str(f))
        rc, out = run(cmd, timeout=600)
        ok = outdir.exists() and any(outdir.rglob("*"))
        detail = f"rc={rc}, output entries={sum(1 for _ in outdir.rglob('*')) if outdir.exists() else 0}"
        if not ok:
            detail += f" | {out[:250]}"
        shutil.rmtree(tmp, ignore_errors=True)
        return emit("DOWNSTREAM", f"{tool} decompile", "PASS" if ok else "FAIL", detail)
    return emit("DOWNSTREAM", "tool", "FAIL", f"unknown tool {tool}")


def check_reproducibility(args) -> int:
    if args.cmd:
        rc, out = run(args.cmd)
        if rc != 0:
            return emit("REPRODUCIBILITY", "command-rerun", "FAIL", f"rc={rc}: {out[:250]}")
        if not args.produces:
            return emit("REPRODUCIBILITY", "command-rerun", "PASS", "command exited 0 (no artifact to hash)")
        prod = Path(args.produces)
        if not prod.exists():
            return emit("REPRODUCIBILITY", "artifact-exists", "FAIL", f"{prod} missing after run")
        h = sha256(prod)
    else:
        if not args.file:
            return emit("REPRODUCIBILITY", "input", "FAIL", "--file or --cmd required")
        h = sha256(Path(args.file))
    if args.expected_sha:
        ok = h.lower() == args.expected_sha.lower()
        return emit("REPRODUCIBILITY", "sha256-stable", "PASS" if ok else "FAIL",
                    f"got {h}", {"sha256": h})
    return emit("REPRODUCIBILITY", "sha256-baseline", "PASS", f"baseline {h}", {"sha256": h})


def gate(paths: list[str]) -> int:
    results, errors = [], []
    for p in paths:
        try:
            results.append(json.loads(Path(p).read_text(encoding="utf-8")))
        except Exception as e:
            errors.append(f"{p}: {e}")
    if not results:
        print(json.dumps({"verdict": "FAILED", "reason": f"no results: {errors}"}))
        return 1
    cats = {}
    for r in results:
        cats.setdefault(r.get("category", "?"), "PASS")
        if r.get("status") != "PASS":
            cats[r["category"]] = "FAIL"
    passed = [c for c, s in cats.items() if s == "PASS"]
    failed = [c for c, s in cats.items() if s == "FAIL"]
    n = len(passed)
    if failed:
        verdict, why = "COMMAND_SUCCESS" if passed else "FAILED", f"categories failed: {failed}"
    elif n >= 3:
        verdict, why = "VERIFIED_SUCCESS", f"{n} categories passed: {passed}"
    else:
        verdict, why = "COMMAND_SUCCESS", f"only {n} category(ies) passed ({passed}); >=3 required"
    out = {"verdict": verdict, "categories_passed": passed, "categories_failed": failed,
           "checks": len(results), "reason": why, "errors": errors}
    print(json.dumps(out, indent=2))
    return {"VERIFIED_SUCCESS": 0, "COMMAND_SUCCESS": 10}.get(verdict, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verification gate for experiment results.")
    sub = ap.add_subparsers(dest="action", required=True)

    s = sub.add_parser("structural"); s.add_argument("--file", required=True)
    s.add_argument("--kind", choices=["zip", "dex", "so", "dir", "file"])
    s = sub.add_parser("parser")
    s.add_argument("--dex"); s.add_argument("--xml"); s.add_argument("--json")
    s = sub.add_parser("content"); s.add_argument("--file", required=True)
    s.add_argument("--entry"); s.add_argument("--class", dest="cls"); s.add_argument("--string")
    s = sub.add_parser("downstream"); s.add_argument("--tool", required=True,
                                                     choices=["apktool", "jadx", "apksigner", "zipalign"])
    s.add_argument("--file", required=True)
    s = sub.add_parser("reproducibility")
    s.add_argument("--file"); s.add_argument("--expected-sha")
    s.add_argument("--cmd"); s.add_argument("--produces")
    s = sub.add_parser("gate"); s.add_argument("results", nargs="+")

    args = ap.parse_args()
    try:
        if args.action == "structural":
            return check_structural(args)
        if args.action == "parser":
            return check_parser(args)
        if args.action == "content":
            return check_content(args)
        if args.action == "downstream":
            return check_downstream(args)
        if args.action == "reproducibility":
            return check_reproducibility(args)
        if args.action == "gate":
            return gate(args.results)
    except Exception as e:
        print(json.dumps({"status": "FAIL", "error": str(e)}))
        return 4
    return 4


if __name__ == "__main__":
    sys.exit(main())
