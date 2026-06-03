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
