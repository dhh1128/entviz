#!/usr/bin/env python3
"""Reject invisible / Trojan-Source Unicode in source files.

Defends against the GlassWorm (invisible payload) and Trojan-Source
(bidi reordering) classes, which cannot be caught by eye or ordinary
linting. Printable non-ASCII (letters, emoji, CJK, box-drawing, em-dashes)
is allowed on purpose; what is refused is anything a reviewer cannot see
or cannot tell apart from a plain space.

Classification is by Unicode general category, so new invisible code points
are refused as Python's Unicode database learns about them, without anyone
having to extend a hand-kept list:

  Cc  controls, except TAB, LF and CR (and CR only as part of CRLF)
  Cf  format characters (bidi controls, zero-width, invisible operators...)
  Co  private use
  Cs  surrogates
  Cn  unassigned
  Zl  line separator,  Zp  paragraph separator
  Zs  space separators other than U+0020

plus, by name, a few code points whose category looks harmless but which
render as nothing: variation selectors, Hangul fillers, U+034F COMBINING
GRAPHEME JOINER and the interlinear annotation characters U+FFF9-FFFB.

The text is examined one character at a time. It is never split with
str.splitlines(), which would treat U+2028, U+0085, VT, FF and friends as
line breaks and so never look at them. Only LF advances the line counter.

Inside a git work tree the scan covers `git ls-files` (tracked files plus
untracked ones that are not ignored). Elsewhere it walks the directory.
Every file that decodes as UTF-8 is scanned, whatever its name, and a NUL
in it is refused like any other control. A file that does not decode is
skipped only when its extension names a binary format (BINARY_SUFFIXES);
anything else that is not UTF-8 is a finding. Sniffing for a NUL byte, as
git does, would let one NUL in a JavaScript comment switch off the scan.

Usage: python3 scripts/check_unicode.py [PATH ...]   (default: ".")
Exits non-zero and prints path:line:col for every finding.
"""
from __future__ import annotations

import subprocess
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
# Larger files are reported, never skipped. GitHub refuses files over 100 MB
# and warns at 50 MB, so a real source file is far below this.
MAX_BYTES = 50 * 1024 * 1024
# Formats that are opaque bytes by design. A file with one of these names is
# still scanned when it happens to decode as UTF-8.
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico", ".bmp",
    ".tif", ".tiff", ".xcf", ".psd", ".pdf", ".woff", ".woff2", ".ttf",
    ".otf", ".eot", ".zip", ".gz", ".tgz", ".bz2", ".xz", ".zst", ".7z",
    ".tar", ".whl", ".jar", ".wasm", ".pyc", ".so", ".dylib", ".dll",
    ".exe", ".class", ".mp3", ".mp4", ".wav", ".flac", ".ogg", ".webm", ".mov",
    ".sqlite", ".sqlite3", ".docx", ".xlsx", ".pptx",
}

BIDI = {0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}
MARKS = {0x200E, 0x200F, 0x061C}
ZW = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD}
HANGUL_FILLERS = {0x115F, 0x1160, 0x3164, 0xFFA0}
ALLOWED_CONTROLS = {0x09, 0x0A, 0x0D}

# General category -> label for anything not caught by name above.
REFUSED_CATEGORIES = {
    "Cc": "control",
    "Cf": "format",
    "Co": "private-use",
    "Cs": "surrogate",
    "Cn": "unassigned",
    "Zl": "line-separator",
    "Zp": "paragraph-separator",
    "Zs": "space",
}


def category(cp):
    """Label for a refused code point, or None when it may appear."""
    if cp < 0x80:
        if cp >= 0x20 and cp != 0x7F or cp in ALLOWED_CONTROLS:
            return None
        return "control"
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
    if cp in HANGUL_FILLERS:
        return "hangul-filler"
    if cp == 0x034F:
        return "invisible"
    if 0xFFF9 <= cp <= 0xFFFB:
        return "interlinear-annotation"
    return REFUSED_CATEGORIES.get(unicodedata.category(chr(cp)))


def find_disallowed(text):
    """(line, col, code point, label) for each refused character, 1-based."""
    out = []
    ln, col = 1, 0
    last = len(text) - 1
    for i, ch in enumerate(text):
        col += 1
        if ch == "\n":
            ln, col = ln + 1, 0
            continue
        cp = ord(ch)
        if ch == "\r":
            # CR belongs to CRLF. A bare CR sends a terminal back to column 1,
            # so whatever follows overprints what came before in `cat` output
            # and CI logs.
            if i == last or text[i + 1] != "\n":
                out.append((ln, col, cp, "control"))
            continue
        cat = category(cp)
        if cat:
            out.append((ln, col, cp, cat))
    return out


def _skipped(rel):
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    # Match against the whole filename, not Path.suffix: the latter returns
    # only the final extension (".js" for "x.min.js"), so a multi-part suffix
    # like ".min.js" would never match.
    return any(rel.name.endswith(s) for s in SKIP_SUFFIXES)


def _git_files(root):
    """Paths git considers part of the tree under root, or None outside git."""
    try:
        res = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others",
             "--exclude-standard"],
            capture_output=True, check=False,
        )
    except OSError:
        return None
    if res.returncode != 0:
        return None
    rels = {r for r in res.stdout.decode("utf-8", "surrogateescape").split("\0") if r}
    return [Path(r) for r in sorted(rels)]


def _candidates(root):
    if root.is_file():
        return [(root, None)]
    rels = _git_files(root)
    if rels is None:
        rels = [p.relative_to(root) for p in sorted(root.rglob("*"))]
    return [(root / rel, rel) for rel in rels]


def iter_files(roots):
    """Text files to scan under each root (explicit files are always kept)."""
    for root in roots:
        for p, rel in _candidates(root):
            # Symlinks are skipped: their target is either scanned in its own
            # right or lies outside the tree. Submodules show up as dirs.
            if p.is_symlink() or not p.is_file():
                continue
            if rel is not None and _skipped(rel):
                continue
            yield p


def scan_file(path):
    """Finding lines for one file."""
    size = path.stat().st_size
    if size > MAX_BYTES:
        # Too big to hold in memory twice. A finding, never a skip, whatever the
        # name, so neither padding nor renaming a file is a way past the gate.
        return [f"{path}: {size} bytes is over the {MAX_BYTES}-byte scan limit (size)"]
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        if path.suffix.lower() in BINARY_SUFFIXES:
            return []
        # Locate the bad byte in characters, as the other findings are.
        prefix = raw[:exc.start].decode("utf-8")
        ln = prefix.count("\n") + 1
        col = len(prefix) - (prefix.rfind("\n") + 1) + 1
        return [f"{path}:{ln}:{col}: not valid UTF-8 (byte 0x{raw[exc.start]:02X}) (encoding)"]
    out = []
    for ln, col, cp, cat in find_disallowed(text):
        name = unicodedata.name(chr(cp), "<unnamed>")
        out.append(f"{path}:{ln}:{col}: U+{cp:04X} {name} ({cat})")
    return out


def main(argv):
    roots = [Path(a) for a in (argv[1:] or ["."])]
    missing = [r for r in roots if not r.exists()]
    for r in missing:
        print(f"check_unicode: {r}: no such file or directory", file=sys.stderr)
    findings = []
    for p in iter_files([r for r in roots if r.exists()]):
        findings.extend(scan_file(p))
    for f in findings:
        print(f)
    if findings:
        print(
            f"\ncheck_unicode: {len(findings)} disallowed character(s) found "
            "(Trojan Source / GlassWorm class).",
            file=sys.stderr,
        )
        return 1
    return 2 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
