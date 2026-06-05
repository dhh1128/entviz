#!/usr/bin/env python3
"""Reject invisible / Trojan-Source Unicode in source files.

Defends against the GlassWorm (invisible payload) and Trojan-Source
(bidi reordering) classes, which cannot be caught by eye or ordinary
linting. Flags only the dangerous categories; ordinary printable
non-ASCII (emoji, CJK, box-drawing, em-dashes) is allowed on purpose.

Usage: python3 scripts/check_unicode.py [PATH ...]   (default: ".")
Exits non-zero and prints path:line:col for every finding.
"""
from __future__ import annotations
import sys
import unicodedata
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "target", "out",
    ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".next", ".turbo", ".gradle", "coverage", ".idea", ".worktrees",
    # entviz-specific build/cache output (Zensical writes the rendered site
    # into /site; uv/zensical cache under .cache). Both are gitignored.
    "site", ".cache",
}
# Tune for this repo: exclude generated/minified files and any test
# fixtures that intentionally embed control characters to exercise them.
SKIP_SUFFIXES = {".min.js", ".map"}
MAX_BYTES = 2 * 1024 * 1024

BIDI = {0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}
MARKS = {0x200E, 0x200F, 0x061C}
ZW = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD}


def category(cp):
    if cp in BIDI:
        return "bidi-control"
    if cp in MARKS:
        return "directional-mark"
    if cp in ZW:
        return "zero-width"
    if 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:
        return "variation-selector"
    if 0xE0000 <= cp <= 0xE007F:
        return "tag-char"
    if 0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0xFFFFD or 0x100000 <= cp <= 0x10FFFD:
        return "private-use"
    return None


def find_disallowed(text):
    out = []
    for ln, line in enumerate(text.splitlines(), 1):
        for col, ch in enumerate(line, 1):
            cat = category(ord(ch))
            if cat:
                out.append((ln, col, ord(ch), cat))
    return out


def iter_files(roots):
    for root in roots:
        cands = [root] if root.is_file() else sorted(root.rglob("*"))
        for p in cands:
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            # Match against the whole filename, not Path.suffix: the latter
            # returns only the final extension (".js" for "x.min.js"), so a
            # multi-part suffix like ".min.js" would never match.
            if any(p.name.endswith(s) for s in SKIP_SUFFIXES):
                continue
            try:
                if p.stat().st_size > MAX_BYTES:
                    continue
                p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            yield p


def main(argv):
    roots = [Path(a) for a in (argv[1:] or ["."])]
    findings = []
    for p in iter_files([r for r in roots if r.exists()]):
        for ln, col, cp, cat in find_disallowed(p.read_text(encoding="utf-8")):
            name = unicodedata.name(chr(cp), "<unnamed>")
            findings.append(f"{p}:{ln}:{col}: U+{cp:04X} {name} ({cat})")
    for f in findings:
        print(f)
    if findings:
        print(
            f"\ncheck_unicode: {len(findings)} disallowed character(s) found "
            "(Trojan Source / GlassWorm class).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
