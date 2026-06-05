"""Tests for the invisible-Unicode / Trojan-Source CI gate (scripts/check_unicode.py).

The gate defends against the GlassWorm (invisible payload) and Trojan-Source
(bidi reordering) attack classes. These tests assert it flags the dangerous
categories AND lets legitimate non-ASCII (accents, CJK, emoji, box-drawing,
em-dashes, arrows) through untouched.

Dangerous code points are constructed with chr(0x...) escapes on purpose — the
literal invisible characters are never pasted into this file (that would defeat
the gate scanning this very test).
"""
import importlib.util
from pathlib import Path

# scripts/ is not an importable package, so load the module from its path.
_SCANNER = Path(__file__).resolve().parent.parent / "scripts" / "check_unicode.py"
_spec = importlib.util.spec_from_file_location("check_unicode", _SCANNER)
check_unicode = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_unicode)


# One representative code point per dangerous category, with the label the
# scanner is expected to report.
DANGEROUS = [
    (0x202E, "bidi-control"),        # RIGHT-TO-LEFT OVERRIDE (Trojan Source)
    (0x2066, "bidi-control"),        # LEFT-TO-RIGHT ISOLATE
    (0x200E, "directional-mark"),    # LEFT-TO-RIGHT MARK
    (0x061C, "directional-mark"),    # ARABIC LETTER MARK
    (0x200B, "zero-width"),          # ZERO WIDTH SPACE
    (0xFEFF, "zero-width"),          # ZERO WIDTH NO-BREAK SPACE / BOM
    (0x00AD, "zero-width"),          # SOFT HYPHEN
    (0xFE0F, "variation-selector"),  # VARIATION SELECTOR-16
    (0xE0101, "variation-selector"), # VARIATION SELECTOR-18 (supplementary)
    (0xE0001, "tag-char"),           # LANGUAGE TAG
    (0xE007F, "tag-char"),           # CANCEL TAG
    (0xE000, "private-use"),         # BMP Private Use Area (GlassWorm decoder)
    (0xF8FF, "private-use"),         # BMP PUA end
    (0xF0000, "private-use"),        # Supplementary PUA-A
    (0x10FFFD, "private-use"),       # Supplementary PUA-B end
]

# Legitimate non-ASCII the project may use on purpose — must NOT be flagged.
LEGITIMATE = [
    0x00E9,   # é  LATIN SMALL LETTER E WITH ACUTE
    0x2014,   # —  EM DASH
    0x2192,   # →  RIGHTWARDS ARROW
    0x2500,   # ─  BOX DRAWINGS LIGHT HORIZONTAL
    0x0394,   # Δ  GREEK CAPITAL LETTER DELTA (used in the paper's formulae)
    0x4E2D,   # 中 CJK
    0x1F600,  # 😀 emoji
]


def test_each_dangerous_category_is_flagged():
    for cp, expected in DANGEROUS:
        assert check_unicode.category(cp) == expected, f"U+{cp:04X}"


def test_legitimate_glyphs_pass():
    for cp in LEGITIMATE:
        assert check_unicode.category(cp) is None, f"U+{cp:04X}"


def test_find_disallowed_reports_line_and_column():
    # A planted RIGHT-TO-LEFT OVERRIDE on the second line, third column.
    text = "clean first line\nab" + chr(0x202E) + "cd"
    findings = check_unicode.find_disallowed(text)
    assert findings == [(2, 3, 0x202E, "bidi-control")]


def test_find_disallowed_passes_legitimate_text():
    text = "résumé → naïve Δx ─ 中文 😀 — em-dash"
    assert check_unicode.find_disallowed(text) == []


# The tests above exercise the two pure functions (category, find_disallowed).
# The ones below close the gap around the directory walk and exit-code contract
# — iter_files() and main() — so the gate's plumbing (which dirs/suffixes/sizes
# it skips, and that a planted payload actually fails CI) is also locked in.

RLO = chr(0x202E)  # RIGHT-TO-LEFT OVERRIDE — a representative Trojan-Source char


def test_main_flags_planted_file_and_reports_location(tmp_path, capsys):
    # A bad char planted in a scanned tree must fail the gate (exit 1) and the
    # offending path + code point must be reported on stdout for the reviewer.
    (tmp_path / "ok.py").write_text("x = 1  # fine\n", encoding="utf-8")
    (tmp_path / "evil.py").write_text("tok = 'a" + RLO + "b'\n", encoding="utf-8")
    assert check_unicode.main(["check_unicode.py", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "evil.py" in captured.out
    assert "U+202E" in captured.out
    assert "(bidi-control)" in captured.out
    # The stderr summary names the attack class so a CI failure is self-explaining.
    assert "Trojan" in captured.err or "GlassWorm" in captured.err


def test_main_returns_zero_for_clean_tree(tmp_path):
    (tmp_path / "clean.py").write_text("y = 2\n", encoding="utf-8")
    assert check_unicode.main(["check_unicode.py", str(tmp_path)]) == 0


def test_iter_files_yields_text_and_skips_binary(tmp_path):
    # Non-UTF-8 bytes exercise the UnicodeDecodeError branch — such files are
    # data/binary, not reviewable source, so the gate must skip them silently.
    (tmp_path / "ok.py").write_text("v = 3\n", encoding="utf-8")
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x01not-utf8")
    names = {p.name for p in check_unicode.iter_files([tmp_path])}
    assert "ok.py" in names
    assert "blob.bin" not in names


def test_iter_files_skips_oversized(tmp_path, monkeypatch):
    # Files larger than MAX_BYTES are presumed data and skipped without being
    # read; shrink the cap so a tiny file trips the same size branch.
    monkeypatch.setattr(check_unicode, "MAX_BYTES", 8)
    (tmp_path / "small.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "big.py").write_text("a = 1  # " + "x" * 64 + "\n", encoding="utf-8")
    names = {p.name for p in check_unicode.iter_files([tmp_path])}
    assert "small.py" in names
    assert "big.py" not in names


def test_iter_files_skips_excluded_dirs_and_suffixes(tmp_path):
    # Vendored/generated trees (SKIP_DIRS) and minified/map artifacts
    # (SKIP_SUFFIXES) are not first-party source and must be excluded — even
    # when they contain a flagged char — so the gate stays signal, not noise.
    skip_dir = next(iter(check_unicode.SKIP_DIRS))
    vendored = tmp_path / skip_dir
    vendored.mkdir()
    (vendored / "lib.py").write_text("z = '" + RLO + "'\n", encoding="utf-8")
    (tmp_path / "bundle.min.js").write_text("q = '" + RLO + "'\n", encoding="utf-8")
    (tmp_path / "real.py").write_text("ok = 1\n", encoding="utf-8")
    names = {p.name for p in check_unicode.iter_files([tmp_path])}
    assert names == {"real.py"}
    # And because the only flagged chars live in skipped locations, the gate passes.
    assert check_unicode.main(["check_unicode.py", str(tmp_path)]) == 0
