"""
CLI entry-point coverage for entviz.app.main().

main() reads sys.argv via argparse and writes the SVG to stdout or a file.
These tests drive it the way a shell would: by setting sys.argv and capturing
stdout / the output file. They cover argument parsing, the aspect-ratio and
font-size validation branches, the ValueError -> parser.error conversion, and
both output modes (stdout and -o FILE).

argparse's parser.error() raises SystemExit(2), so the rejection cases assert
SystemExit with code 2.
"""
import sys

import pytest

from entviz.app import main, ASPECT_RATIO_PAT

# A 256-bit hex string — a valid, recognized entropy input.
HEX = "deadbeef" * 8


def _run(monkeypatch, *argv):
    """Invoke main() with the given CLI args (argv after the program name)."""
    monkeypatch.setattr(sys, "argv", ["entviz", *argv])
    main()


# --- stdout output mode --------------------------------------------------

def test_renders_svg_to_stdout(monkeypatch, capsys):
    _run(monkeypatch, HEX)
    out = capsys.readouterr().out
    assert out.startswith("<svg")
    assert out.endswith("\n")


def test_default_invocation_needs_only_entropy(monkeypatch, capsys):
    # No --ar/--fs/-o: defaults (1:1, 12pt, stdout) must produce valid output.
    _run(monkeypatch, HEX)
    assert "<svg" in capsys.readouterr().out


# --- file output mode (-o / --output) ------------------------------------

def test_writes_svg_to_output_file(monkeypatch, capsys, tmp_path):
    dest = tmp_path / "out.svg"
    _run(monkeypatch, HEX, "-o", str(dest))
    # Nothing on stdout in file mode.
    assert capsys.readouterr().out == ""
    contents = dest.read_text(encoding="utf-8")
    assert contents.startswith("<svg")


def test_output_long_flag_equivalent(monkeypatch, tmp_path):
    dest = tmp_path / "out.svg"
    _run(monkeypatch, HEX, "--output", str(dest))
    assert dest.read_text(encoding="utf-8").startswith("<svg")


# --- aspect-ratio parsing and validation ---------------------------------

def test_aspect_ratio_pattern_matches_ratio():
    m = ASPECT_RATIO_PAT.match("16:9")
    assert m is not None
    assert m.groups() == ("16", "9")


@pytest.mark.parametrize("ratio", ["3:2", "1:1", "100:100"])
def test_valid_aspect_ratio_renders(monkeypatch, capsys, ratio):
    _run(monkeypatch, HEX, "--ar", ratio)
    assert "<svg" in capsys.readouterr().out


@pytest.mark.parametrize("ratio", ["0:1", "1:0", "101:1", "1:101"])
def test_out_of_range_aspect_ratio_is_rejected(monkeypatch, ratio):
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, HEX, "--ar", ratio)
    assert exc.value.code == 2


def test_unparseable_aspect_ratio_falls_back_to_square(monkeypatch, capsys):
    # A string that doesn't match RATIO leaves the 1:1 default in place rather
    # than erroring — documents the current lenient behavior.
    _run(monkeypatch, HEX, "--ar", "not-a-ratio")
    assert "<svg" in capsys.readouterr().out


# --- font-size validation ------------------------------------------------

@pytest.mark.parametrize("fs", ["6", "12", "30"])
def test_valid_font_size_renders(monkeypatch, capsys, fs):
    _run(monkeypatch, HEX, "--fs", fs)
    assert "<svg" in capsys.readouterr().out


@pytest.mark.parametrize("fs", ["5", "31", "0"])
def test_out_of_range_font_size_is_rejected(monkeypatch, fs):
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, HEX, "--fs", fs)
    assert exc.value.code == 2


def test_non_integer_font_size_is_rejected_by_argparse(monkeypatch):
    # type=int means argparse rejects a non-integer before our range check.
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, HEX, "--fs", "big")
    assert exc.value.code == 2


# --- ValueError -> parser.error conversion -------------------------------

def test_empty_entropy_becomes_parser_error(monkeypatch):
    # render("") raises ValueError; main() converts it to parser.error (exit 2)
    # rather than letting the traceback escape.
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, "")
    assert exc.value.code == 2


def test_oversized_entropy_becomes_parser_error(monkeypatch):
    from entviz.pipeline import MAX_INPUT_CHARS
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, "d" * (MAX_INPUT_CHARS + 1))
    assert exc.value.code == 2


# --- note pass-through ----------------------------------------------------

def test_note_is_passed_through(monkeypatch, capsys):
    _run(monkeypatch, HEX, "--note", "abc123")
    out = capsys.readouterr().out
    assert "<svg" in out
    assert "abc123" in out


def test_invalid_note_becomes_parser_error(monkeypatch):
    # A non-ASCII note fails sanitize_note -> ValueError -> parser.error.
    # (Spaces and punctuation are valid now; the charset is printable ASCII.)
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, HEX, "--note", "café")
    assert exc.value.code == 2
