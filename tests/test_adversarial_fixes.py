"""
Regression tests for the adversarial-review findings in
reviews/adversarial-2026-05-27.md (F1, F2, F3, F4, F-A11).

Each test pins a single failure mode that was confirmed in the review.
The fixes themselves are intentionally narrow and live in
entviz/entropy.py (parser dispatch order, disproof-path case
normalization, odd-length guard on parse_hex_multihash, BCH regex
end-anchor) — see the review file for the full rationale and the
collision-candidate inputs at /tmp/entviz-collision-candidates.txt.
"""
from entviz.entropy import parse
from entviz.pipeline import render


# ---------------------------------------------------------------------------
# F1 — parser dispatch order: lowercase pure hex must not be silently
# misclassified as EOS. The fix is to ensure parse_hex runs before
# parse_eos_address so that genuine hex wins.
# ---------------------------------------------------------------------------

def test_f1_lowercase_short_hex_parses_as_hex_not_eos():
    """`ff112233` is pure lowercase hex; must classify as hex."""
    p = parse("ff112233")
    assert p is not None
    assert p.type == "hex", f"expected hex, got {p.type!r}"


def test_f1_lowercase_short_hex_letters_parses_as_hex_not_eos():
    """`abcdef12` is pure lowercase hex; must classify as hex."""
    p = parse("abcdef12")
    assert p is not None
    assert p.type == "hex", f"expected hex, got {p.type!r}"


def test_f1_hex_case_invariant_render():
    """`ff112233` and `FF112233` render to the same SVG (case-normalized)."""
    assert render("ff112233") == render("FF112233")


def test_f1_genuine_short_eos_still_parses_as_eos():
    """A genuine 12-char EOS-shaped non-hex input still parses as EOS."""
    # 12 chars, alphabet [a-z1-5.], last char in [a-j1-5] — contains
    # characters (g, p, v, o, y, z) not in the hex alphabet.
    p = parse("gqgpv4222oyz")
    assert p is not None
    assert p.type == "EOS", f"expected EOS, got {p.type!r}"


# ---------------------------------------------------------------------------
# F2 — disproof-path case normalization: BASE32 (and HEX) must be
# lowercased on the disproof path so case-insensitive alphabets hash
# the same regardless of input case.
# ---------------------------------------------------------------------------

def test_f2_base32_disproof_case_normalized_core():
    """An uppercase-only BASE32 input and its lowercase form parse to the
    same core via the disproof path.

    Choice of input: the input must include at least one BASE32-only
    character (`6` or `7`) so it cannot be caught by parse_hex; and at
    least one character outside `[a-z1-5.]` so it cannot be caught by
    parse_eos_address — otherwise lowercase forms would be intercepted
    by EOS before reaching the disproof path. `MNPQRS67` satisfies both:
    M/N/P/Q/R/S are base32 alphabet letters but not all in EOS's
    lowercase superset, and `6`/`7` rule out hex.

    Pre-F2-fix behavior: upper.core='MNPQRS67', lower.core='mnpqrs67' —
    disproof passed through input case verbatim. Post-fix: both
    lowercased.
    """
    upper = parse("MNPQRS67")
    lower = parse("mnpqrs67")
    assert upper is not None
    assert lower is not None
    assert upper.core == lower.core, (
        f"case-normalized cores must match: {upper.core!r} vs {lower.core!r}"
    )
    assert upper.alphabet.name == "base32"


def test_f2_base32_case_invariant_render():
    """render of base32 input is case-invariant for the disproof path
    (same input rationale as the test above)."""
    assert render("MNPQRS67") == render("mnpqrs67")


# ---------------------------------------------------------------------------
# F3 — odd-length all-hex input must not raise. parse_hex_multihash
# previously called bytes.fromhex(text) without guarding length parity.
# ---------------------------------------------------------------------------

def test_f3_odd_length_hex_badcafe_does_not_raise():
    parse("badcafe")  # must not raise


def test_f3_odd_length_hex_1234567_does_not_raise():
    parse("1234567")  # must not raise


def test_f3_odd_length_hex_aaaaaaa_does_not_raise():
    parse("aaaaaaa")  # must not raise


def test_f3_odd_length_hex_7abcdef_does_not_raise():
    parse("7abcdef")  # must not raise


# ---------------------------------------------------------------------------
# F4 — BITCOIN_CASH_REGEX needs the $ anchor so trailing bytes do not
# get silently truncated.
# ---------------------------------------------------------------------------

def test_f4_bch_with_trailing_text_does_not_match_bch():
    """A valid BCH-shaped 42-char prefix followed by spaces+text must
    NOT be classified as BCH (silent truncation attack)."""
    text = "pqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq EXTRA_TEXT"
    p = parse(text)
    # We don't assert what it WILL be (UTF-8 fallback or otherwise), only
    # that it does NOT pretend to be a BCH address.
    assert p is None or p.type != "BCH", (
        f"input with trailing text should not match BCH, got {p!r}"
    )


def test_f4_legitimate_bch_still_matches():
    """Exactly 42 bech32 chars after the optional prefix is the
    legitimate BCH shape — must still be classified as BCH."""
    text = "pqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"
    assert len(text) == 42
    p = parse(text)
    assert p is not None
    assert p.type == "BCH", f"expected BCH, got {p!r}"


def test_f4_bch_shaped_inputs_differing_in_suffix_render_differently():
    """Two BCH-shaped strings sharing their first 42 chars but
    differing after must produce different entvizes (i.e., the regex
    no longer truncates them down to an identical prefix)."""
    a = "pqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq SUFFIX_A"
    b = "pqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq SUFFIX_B"
    assert render(a) != render(b)


# ---------------------------------------------------------------------------
# F-A11 — SVG injection regression: hostile cell-text input must be
# HTML-escaped in the rendered SVG (lxml's .text= assignment already
# does this; the test pins the behavior against future regression if
# the renderer is ever rewritten with string concatenation).
# ---------------------------------------------------------------------------

def test_fa11_svg_injection_is_escaped():
    """Hostile markup must never reach the SVG unescaped (F-A11). Two layers:

    1. A DID URL carrying a <script> payload is DROPPED entirely as of v11 —
       the DID URL (path/query/fragment) is a FREE annotation, no longer
       surfaced as a rendered suffix (this.i:d1dm3th0; docs/spec.md
       *Decentralized Identifiers*). So the payload never reaches the SVG at
       all — strictly stronger than escaping.
    2. For user-controlled text that DOES still land in a text element — the
       user note, which is printable-ASCII and so may contain '<' — lxml
       escaping is the defense.

    (The former SSH-comment vector is likewise closed by dropping the free
    annotation — see test_v4_ssh_keys.test_ssh_comment_does_not_affect_rendering
    and this.i:sufxbind. A bare '<script>...' fed as the entropy goes through
    the UTF-8→base64url fallback and never appears verbatim either.)
    """
    # Layer 1 — the DID URL and its payload are dropped, not rendered.
    out = render("did:web:example.com/<script>alert(1)</script>")
    assert "did:web:" in out, "the DID itself should still render (label)"
    assert "<script" not in out, "raw <script must not appear (DID URL dropped)"
    assert "&lt;script" not in out, (
        "the DID URL is DROPPED as a free annotation (v11), so the payload "
        "must not appear at all — not even escaped"
    )

    # Layer 2 — a hostile user note DOES reach a text element and MUST be escaped.
    noted = render("ff112233", note="<script>")
    assert "&lt;script" in noted, "user note '<' must be lxml-escaped"
    assert "<script" not in noted, "raw <script must not appear from the note"


# ---------------------------------------------------------------------------
# F6 (adversarial-2026-06-02) — short odd-length all-hex fragments were
# mislabeled EOS (base64-tokenized) because parse_hex returns None for
# odd-length input and EOS caught the fall-through. EOS must not claim a
# string that is entirely hex-alphabet characters.
# ---------------------------------------------------------------------------

def test_f6_short_odd_length_hex_fragment_is_not_eos():
    """'badcafe' is a 7-char hex fragment, not an EOS account."""
    p = parse("badcafe")
    assert p.type != "EOS", f"expected non-EOS, got {p.type!r}"
    assert p.type == "hex"


def test_f6_hex_fragment_classification_is_length_parity_stable():
    """A hex fragment and the same fragment with one more nibble classify
    the same way (both hex), instead of flipping EOS<->hex across parity."""
    assert parse("badcafe").type == parse("badcafe0").type == "hex"


def test_f6_genuine_eos_with_nonhex_chars_still_parses_as_eos():
    """EOS names containing a char outside the hex alphabet are unaffected."""
    assert parse("gqgpv4222oyz").type == "EOS"
    assert parse("eosio.token").type == "EOS"
