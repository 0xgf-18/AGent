#!/usr/bin/env python3
"""
KB ID allocator.

Scans knowledge_base/wiki/**/*.md (frontmatter AND body) for ID patterns and
allocates the next free sequential ID for a given prefix. IDs are never reused:
the allocator always returns (max_seen + 1), even if an article was deleted.

ID formats (see .kb/schemas/*):
    A-XXXXXX    APK analysis            (6 digits)
    EXP-XXXX    experiment              (4 digits)
    ST-XXXX     success trace           (4 digits)
    T-XXXX      technique               (4 digits)
    ART-XXXX    artifact                (4 digits)
    P-XXXX      pattern                 (4 digits)
    KD-XXXX     knowledge diff          (4 digits)
    TR-XXXX     tool registry           (4 digits)

Usage:
    python kb_ids.py --list                 # all prefixes: current max + next
    python kb_ids.py --next EXP             # print next ID for prefix EXP
    python kb_ids.py --next analysis        # alias accepted too
    python kb_ids.py --has T-0019           # exit 0 if ID already exists
"""

import argparse
import re
import sys
from pathlib import Path

PREFIX_MAP = {
    "A": ("A", 6),
    "ANALYSIS": ("A", 6),
    "EXP": ("EXP", 4),
    "EXPERIMENT": ("EXP", 4),
    "ST": ("ST", 4),
    "SUCCESS": ("ST", 4),
    "T": ("T", 4),
    "TECHNIQUE": ("T", 4),
    "ART": ("ART", 4),
    "ARTIFACT": ("ART", 4),
    "P": ("P", 4),
    "PATTERN": ("P", 4),
    "KD": ("KD", 4),
    "DIFF": ("KD", 4),
    "TR": ("TR", 4),
    "TOOL": ("TR", 4),
}

# Order matters: longer prefixes first so TR- is matched before T-.
PATTERNS = [
    ("A", re.compile(r"\bA-(\d{6})\b")),
    ("EXP", re.compile(r"\bEXP-(\d{4})\b")),
    ("ST", re.compile(r"\bST-(\d{4})\b")),
    ("TR", re.compile(r"\bTR-(\d{4})\b")),
    ("KD", re.compile(r"\bKD-(\d{4})\b")),
    ("ART", re.compile(r"\bART-(\d{4})\b")),
    ("T", re.compile(r"\bT-(\d{4})\b")),
    ("P", re.compile(r"\bP-(\d{4})\b")),
]


def kb_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def scan(wiki_dir: Path) -> dict:
    """Return {prefix: max_numeric_value_seen} across the whole wiki."""
    maxima = {p: 0 for p, _ in PATTERNS}
    if not wiki_dir.is_dir():
        return maxima
    for md in wiki_dir.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for prefix, rx in PATTERNS:
            for m in rx.finditer(text):
                val = int(m.group(1))
                if val > maxima[prefix]:
                    maxima[prefix] = val
    return maxima


def fmt(prefix: str, value: int) -> str:
    _, width = PREFIX_MAP[prefix.upper()]
    return f"{prefix}-{value:0{width}d}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Allocate knowledge-base IDs.")
    ap.add_argument("--list", action="store_true", help="show current max and next ID for every prefix")
    ap.add_argument("--next", metavar="PREFIX", help="print the next free ID for a prefix (e.g. EXP, T, A)")
    ap.add_argument("--has", metavar="ID", help="check whether an ID (e.g. T-0019) already exists")
    ap.add_argument("--wiki", metavar="DIR", help="override wiki directory")
    args = ap.parse_args()

    wiki_dir = Path(args.wiki) if args.wiki else kb_root() / "knowledge_base" / "wiki"
    maxima = scan(wiki_dir)

    if args.has:
        m = re.match(r"^([A-Z]+)-(\d+)$", args.has.upper())
        if not m:
            print(f"malformed ID: {args.has}", file=sys.stderr)
            return 2
        prefix = m.group(1)
        width = len(m.group(2))
        for p, rx in PATTERNS:
            if p == prefix:
                target = int(m.group(2))
                found = False
                for md in (wiki_dir.rglob("*.md") if wiki_dir.is_dir() else []):
                    try:
                        text = md.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    if rx.search(text):
                        found = True
                        break
                print(f"{args.has.upper()}: {'EXISTS' if found else 'FREE'}")
                return 0 if found else 1
        print(f"unknown prefix in: {args.has}", file=sys.stderr)
        return 2

    if args.next:
        key = args.next.upper()
        if key not in PREFIX_MAP:
            print(f"unknown prefix: {args.next} (known: {sorted(set(PREFIX_MAP))})", file=sys.stderr)
            return 2
        canonical, _ = PREFIX_MAP[key]
        current = maxima.get(canonical, 0)
        print(fmt(canonical, current + 1))
        return 0

    # default: --list
    out = {}
    for prefix, _ in PATTERNS:
        current = maxima[prefix]
        out[prefix] = {"max": current, "next": fmt(prefix, current + 1)}
    import json
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
