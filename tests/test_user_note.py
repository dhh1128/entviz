"""
User note caption (`--note` / render(note=...)).

An out-of-band, aggressively-sanitized, visually-quiet caption rendered in
the bottom strip. It never enters the entropy/fingerprint and is outside the
comparison surface. See `this.i:usrn0te1` and spec.md "User note".
"""
import re

import pytest

from entviz.pipeline import render, sanitize_note


HEX = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"  # no suffix
LEI = "5493001KJTIIGC8Y1R12"  # parses with a 2-char checksum suffix


def _clip_digest(svg):
    m = re.search(r'grid-clip-([0-9a-f]{16})-(\d+x\d+)', svg)
    assert m, "no clip id found"
    return m.group(0)


# ---- sanitization ------------------------------------------------------


def test_sanitize_accepts_printable_ascii_and_preserves_case():
    assert sanitize_note("git") == "git"
    assert sanitize_note("GitV2") == "GitV2"          # case preserved
    assert sanitize_note("two words") == "two words"  # spaces are valid now
    assert sanitize_note("a.b_c-d!") == "a.b_c-d!"    # punctuation is valid now
    assert sanitize_note("0123456789") == "0123456789"  # 10 chars, the max


def test_sanitize_none_and_empty_are_no_note():
    assert sanitize_note(None) is None
    assert sanitize_note("") is None


def test_sanitize_rejects_too_long():
    with pytest.raises(ValueError):
        sanitize_note("abcdefghijk")  # 11 chars > 10


@pytest.mark.parametrize("bad", [
    "café", "gît", "naïve",        # non-ASCII letters (closes the homoglyph surface)
    "ab\tcd", "x\x07y", "a\nb",    # control characters
    "emoji\U0001F600",             # non-ASCII (emoji)
    "x\u202ey",                    # bidi override (Trojan-Source)
    "a\u200bb",                    # zero-width space
])
def test_sanitize_rejects_non_printable_ascii(bad):
    with pytest.raises(ValueError):
        sanitize_note(bad)


# ---- rendering ---------------------------------------------------------


def test_note_renders_gray_with_data_attribute():
    svg = render(HEX, note="git")
    assert 'data-user-note="git"' in svg
    assert '(git)' in svg
    # Gray #808080 as a FILL is unique to the note (borders use it as a
    # stroke), so its presence/absence is a clean signal.
    assert 'fill="#808080"' in svg


def test_no_note_means_no_note_markup():
    svg = render(HEX)
    assert 'data-user-note' not in svg
    assert 'fill="#808080"' not in svg


def test_note_only_input_gets_a_bottom_strip():
    # HEX has no suffix; a note alone must still produce the bottom strip.
    with_note = render(HEX, note="git")
    without = render(HEX)
    assert 'data-channel="label-bottom"' in with_note
    assert 'data-channel="label-bottom"' not in without


def test_note_follows_an_existing_suffix():
    svg = render(LEI, note="git")
    # suffix (the LEI check digits) and the note both appear, note last.
    assert '...' in svg and '(git)' in svg
    assert 'data-user-note="git"' in svg


def test_note_does_not_change_the_fingerprint_or_grid():
    # Same value, with and without a note: the fingerprint stamp (and grid
    # dimensions) embedded in the clip id must be identical.
    assert _clip_digest(render(HEX, note="git")) == _clip_digest(render(HEX))


def test_note_xml_special_chars_are_escaped():
    # < > & " are valid printable ASCII, so they are accepted — and MUST be
    # XML-escaped in both the text node and the data-user-note attribute. This
    # is the load-bearing injection control now that the charset is relaxed.
    svg = render(HEX, note='a<b>&"x')
    assert 'data-user-note="a&lt;b&gt;&amp;&quot;x"' in svg
    assert '(a&lt;b&gt;&amp;"x)' in svg          # text node: < > & escaped
    assert '<b>' not in svg                       # no raw injected element


def test_invalid_note_raises_from_render():
    with pytest.raises(ValueError):
        render(HEX, note="too-long-and-bad!")  # 17 chars > 10
