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


# ---------------------------------------------------------------------------
# Gaps closed in the 2026-11 hardening pass. Each test below failed against the
# previous scanner, which read with str.splitlines(), kept hand-maintained sets
# of "dangerous" code points, skipped non-UTF-8 and oversized files silently,
# and walked the filesystem instead of asking git what is in the repo.

# str.splitlines() treats all of these as line breaks, so the old scanner
# consumed them as separators and never examined them.
SPLITLINES_BREAKS = [0x2028, 0x2029, 0x0085, 0x000B, 0x000C, 0x001C, 0x001D, 0x001E]


def test_splitlines_breaks_are_examined_not_consumed():
    for cp in SPLITLINES_BREAKS:
        text = "a = 1\nb" + chr(cp) + "c\n"
        findings = check_unicode.find_disallowed(text)
        assert [(ln, col, got) for ln, col, got, _ in findings] == [(2, 2, cp)], f"U+{cp:04X}"


def test_only_lf_advances_the_line_counter():
    # A U+2028 must not shift later findings onto a phantom line.
    text = "x" + chr(0x2028) + "y\nz" + RLO + "\n"
    lines = [ln for ln, _, _, _ in check_unicode.find_disallowed(text)]
    assert lines == [1, 2]


# Every space separator other than U+0020 renders as (or near) a plain space,
# so a reviewer cannot tell it apart from one. U+1680 is the one that beat the
# testigo SVG logo check.
NON_ASCII_SPACES = [0x00A0, 0x1680, 0x2002, 0x2009, 0x200A, 0x202F, 0x205F, 0x3000]


def test_non_ascii_spaces_are_flagged():
    for cp in NON_ASCII_SPACES:
        assert check_unicode.category(cp) == "space", f"U+{cp:04X}"


# Code points that render as nothing (or nearly nothing) but fall outside the
# old hand-kept sets.
INVISIBLE_OTHERS = [
    (0x115F, "hangul-filler"),
    (0x1160, "hangul-filler"),
    (0x3164, "hangul-filler"),
    (0xFFA0, "hangul-filler"),
    (0x034F, "invisible"),               # COMBINING GRAPHEME JOINER
    (0x180E, "format"),                  # MONGOLIAN VOWEL SEPARATOR
    (0x2061, "format"),                  # FUNCTION APPLICATION
    (0x2064, "format"),                  # INVISIBLE PLUS
    (0xFFF9, "interlinear-annotation"),
    (0xFFFB, "interlinear-annotation"),
    (0x001B, "control"),                 # ESC: terminal escape sequences
    (0x0000, "control"),
    (0x007F, "control"),                 # DELETE
    (0x009B, "control"),                 # C1 CONTROL SEQUENCE INTRODUCER
]


def test_other_invisibles_and_controls_are_flagged():
    for cp, expected in INVISIBLE_OTHERS:
        assert check_unicode.category(cp) == expected, f"U+{cp:04X}"


def test_unassigned_code_point_is_flagged():
    # U+0378 has never been assigned; a future assignment would show up here as
    # a test failure on a newer Python, which is the cue to pick another.
    assert check_unicode.category(0x0378) == "unassigned"


def test_tab_lf_crlf_pass_and_bare_cr_is_flagged():
    assert check_unicode.find_disallowed("a\tb\r\nc\n") == []
    # A bare CR returns a terminal's cursor to column 1, so text after it
    # overprints text before it in `cat` and in CI logs.
    assert check_unicode.find_disallowed("safe\rEVIL\n") == [(1, 5, 0x0D, "control")]


def test_main_fails_on_non_utf8_text(tmp_path, capsys):
    # Latin-1 bytes with no NUL: text, but not UTF-8. The old scanner skipped
    # it, so anything at all could hide inside.
    (tmp_path / "latin1.txt").write_bytes(b"caf\xe9\n")
    assert check_unicode.main(["check_unicode.py", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "latin1.txt" in out
    assert "not valid UTF-8" in out


def test_main_scans_large_files(tmp_path):
    # The old 2 MiB cap made "pad the file" a bypass.
    big = "x = 1\n" * (3 * 1024 * 1024 // 6) + "y = '" + RLO + "'\n"
    (tmp_path / "big.py").write_text(big, encoding="utf-8")
    assert check_unicode.main(["check_unicode.py", str(tmp_path)]) == 1


def _git(cwd, *args):
    import subprocess
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def test_git_repo_scan_uses_ls_files(tmp_path):
    # Inside a work tree the scan covers what git tracks plus untracked files
    # that are not ignored, and nothing else. An ignored scratch file holding a
    # payload is not the repo's content, and an untracked new file is, since it
    # is one `git add` away from a commit.
    _git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text("scratch/\n", encoding="utf-8")
    (tmp_path / "scratch").mkdir()
    (tmp_path / "scratch" / "notes.txt").write_text(RLO + "\n", encoding="utf-8")
    (tmp_path / "tracked.py").write_text("a = 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".gitignore", "tracked.py")
    (tmp_path / "new.py").write_text("b = 2\n", encoding="utf-8")
    names = {p.name for p in check_unicode.iter_files([tmp_path])}
    assert names == {".gitignore", "tracked.py", "new.py"}
    assert check_unicode.main(["check_unicode.py", str(tmp_path)]) == 0
    (tmp_path / "new.py").write_text("b = '" + RLO + "'\n", encoding="utf-8")
    assert check_unicode.main(["check_unicode.py", str(tmp_path)]) == 1


def test_this_repo_passes_its_own_gate():
    # The gate is only worth something if the tree it guards is clean, so a
    # regression here (a pasted NBSP, an emoji with U+FE0F) fails locally,
    # before CI does.
    root = _SCANNER.parent.parent
    assert check_unicode.main(["check_unicode.py", str(root)]) == 0
