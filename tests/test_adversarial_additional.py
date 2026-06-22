"""
Regression tests for the additional patterns flagged in the adversarial
review (reviews/adversarial-2026-05-27.md, "Additional Patterns Noted"
section): F-A1, F-A2, F-A3, F-A4, F-A5.

Each fix is intentionally narrow:
  * F-A1: thread-safe _DISPROOF_ORDER init (no race on first concurrent
    call to detect_alphabet_by_disproof / parse).
  * F-A2: 0X and 0x prefixes on Ethereum addresses route through the same
    parser path and produce identical Parsed.type labels.
  * F-A3: clipPath id salt widened from 8 to 16 hex chars (32-bit ->
    64-bit collision resistance).
  * F-A4: root <svg> carries a viewBox attribute matching its
    width/height so responsive embeds scale correctly.
  * F-A5: font-family is a documented cross-platform fallback chain
    (JetBrains Mono / Menlo / Consolas / DejaVu Sans Mono / Liberation
    Mono / Roboto Mono / Noto Sans Mono / monospace), not bare `monospace`
    (which lets each viewer's OS pick its own glyph metrics).
"""
import re
from concurrent.futures import ThreadPoolExecutor

import pytest
from lxml import etree

from entviz.entropy import (
    detect_alphabet_by_disproof,
    parse,
    HEX,
    BASE32,
    BECH32,
    BASE58,
    BASE64,
    BASE64URL,
)
from entviz.pipeline import render


FONT_CHAIN = ('"JetBrains Mono", "Menlo", "Consolas", "DejaVu Sans Mono", '
              '"Liberation Mono", "Roboto Mono", "Noto Sans Mono", monospace')


# ---------------------------------------------------------------------------
# F-A1 — _DISPROOF_ORDER must be safe under concurrent first-call from
# multiple threads. Pre-fix: lazy mutation of a module global created a
# small race window where two threads could each build & assign the
# list, with the second clobbering the first mid-iteration of the
# detector loop in the first.
# ---------------------------------------------------------------------------

def test_fa1_disproof_order_thread_safe_under_concurrent_calls():
    """8 threads x 100 calls each. No exceptions, all answers consistent
    with the single-threaded baseline.

    Post-fix, `_DISPROOF_ORDER` is populated at module import time so no
    lazy-init race can occur. This test guards against a regression to
    the lazy form: if someone reverts to `_DISPROOF_ORDER = None` +
    in-function init, a concurrent stampede of first-callers becomes
    possible again. The test asserts (a) no exception is raised on
    concurrent calls and (b) every worker sees results consistent with
    the single-threaded baseline.
    """
    import entviz.entropy as entropy_mod
    # Confirm precondition for the fix: the global is already populated
    # at import time (eager-init approach (a)). If a future maintainer
    # reverts to lazy init, this assertion is the early-warning.
    assert entropy_mod._DISPROOF_ORDER is not None, (
        "_DISPROOF_ORDER must be populated at module import time "
        "(F-A1 fix). If you switched to lazy init, also add a "
        "threading.Lock-guarded double-checked init pattern."
    )
    # Seed inputs covering each disproof alphabet so the loop does real
    # work, not just trivial early-returns.
    inputs = [
        "deadbeef",          # HEX
        "MNPQRS67",          # BASE32 (also tested by F2)
        "qpzry9x8",          # BECH32
        "1A2B3C4D5E",        # BASE58 (case-sensitive)
        "abc+def/123",       # BASE64
        "abc-def_123",       # BASE64URL
        "Hello, world!",     # falls through to None (not an alphabet)
    ]
    baseline = [detect_alphabet_by_disproof(s) for s in inputs]

    def worker():
        results = []
        for _ in range(100):
            for s in inputs:
                results.append(detect_alphabet_by_disproof(s))
        return results

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(worker) for _ in range(8)]
        all_results = [f.result() for f in futures]

    # Every worker's results must equal the baseline pattern, repeated.
    for results in all_results:
        # results length = 100 * len(inputs); pattern repeats every
        # len(inputs).
        assert len(results) == 100 * len(inputs)
        for i, r in enumerate(results):
            assert r == baseline[i % len(inputs)], (
                f"thread saw inconsistent answer at offset {i}: "
                f"{r!r} vs baseline {baseline[i % len(inputs)]!r}"
            )


def test_fa1_disproof_order_thread_safe_via_parse():
    """Same race, exercised through the public parse() entry point
    (which calls detect_alphabet_by_disproof for inputs no specific
    parser matched)."""
    inputs = ["MNPQRS67", "mnpqrs67", "qpzry9x8", "abc+def/"]
    baseline = [parse(s) for s in inputs]

    def worker():
        return [parse(s) for s in inputs for _ in range(50)]

    with ThreadPoolExecutor(max_workers=6) as ex:
        results_list = [f.result() for f in [ex.submit(worker) for _ in range(6)]]

    for results in results_list:
        for i, r in enumerate(results):
            expected = baseline[i // 50]
            assert r == expected, (
                f"parse() returned inconsistent result under concurrency: "
                f"{r!r} vs {expected!r}"
            )


# ---------------------------------------------------------------------------
# F-A2 — Ethereum '0X' (capital X) prefix must route identically to '0x'.
# Pre-fix: the ETHEREUM_REGEX accepts either via re.I, but parse_hex
# winning the race for a 40-hex body would have produced a `hex(40)`
# label instead of `ETH` for one of the two cases.
# ---------------------------------------------------------------------------

# A real Ethereum address body (40 hex chars), all-lowercase so EIP-55
# validation is skipped (lenient: single-case body = "checksum not
# asserted"). This isolates the prefix-case behavior.
_ETH_BODY = "deadbeefcafebabe1234567890abcdef12345678"


def test_fa2_ethereum_capital_X_prefix_parses_as_eth():
    p = parse("0X" + _ETH_BODY)
    assert p is not None
    assert p.type == "ETH", f"expected ETH, got {p.type!r}"


def test_fa2_ethereum_capital_X_matches_lowercase_x():
    p_upper = parse("0X" + _ETH_BODY)
    p_lower = parse("0x" + _ETH_BODY)
    assert p_upper.type == p_lower.type, (
        f"type labels diverged: 0X -> {p_upper.type!r}, "
        f"0x -> {p_lower.type!r}"
    )
    assert p_upper.alphabet == p_lower.alphabet
    assert p_upper.core == p_lower.core


def test_fa2_ethereum_capital_X_renders_identically():
    """Stronger check: the entire SVG matches across the two prefix
    cases. Note: the prefix is stored as '0x' in both cases after
    normalization, so the label strip will read identically too."""
    assert render("0X" + _ETH_BODY) == render("0x" + _ETH_BODY)


# ---------------------------------------------------------------------------
# F-A3 — clipPath id must use 16 hex chars of fingerprint salt, not 8.
# Format: grid-clip-{first_16_hex}-{cols}x{rows}.
# ---------------------------------------------------------------------------

_CLIP_ID_RE = re.compile(
    r'^grid-clip-([0-9a-f]{16})-(\d+)x(\d+)$'
)


def _root(svg_str):
    return etree.fromstring(svg_str.encode("utf-8"))


def test_fa3_clip_id_uses_16_hex_chars():
    out = render("deadbeef")
    root = _root(out)
    clip_paths = root.findall(".//{http://www.w3.org/2000/svg}clipPath")
    assert len(clip_paths) == 1, f"expected exactly one clipPath, got {len(clip_paths)}"
    clip_id = clip_paths[0].get("id")
    m = _CLIP_ID_RE.match(clip_id)
    assert m is not None, (
        f"clipPath id {clip_id!r} does not match "
        f"grid-clip-XXXXXXXXXXXXXXXX-NxM (16 hex chars)"
    )


def test_fa3_clip_id_referenced_consistently():
    """The url(#…) reference in the ellipse layer must point at the
    same id the clipPath defines."""
    out = render("deadbeef")
    root = _root(out)
    clip_id = root.findall(".//{http://www.w3.org/2000/svg}clipPath")[0].get("id")
    # Find at least one element with clip-path="url(#<id>)" pointing
    # at our id.
    ref = f"url(#{clip_id})"
    matches = [
        el for el in root.iter()
        if el.get("clip-path") == ref
    ]
    assert matches, (
        f"no element references clip-path={ref!r} — id mismatch between "
        f"definition and consumer"
    )


# ---------------------------------------------------------------------------
# F-A4 — root <svg> must carry viewBox="0 0 W H" matching width/height.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("inp", ["deadbeef", "deadbeefcafebabe" * 4])
def test_fa4_root_svg_has_viewbox_matching_width_height(inp):
    out = render(inp)
    root = _root(out)
    width = root.get("width")
    height = root.get("height")
    view_box = root.get("viewBox")
    assert width is not None and height is not None
    assert view_box is not None, "root <svg> is missing viewBox attribute"
    expected = f"0 0 {width} {height}"
    assert view_box == expected, (
        f"viewBox {view_box!r} does not match 0 0 {width} {height}"
    )


# ---------------------------------------------------------------------------
# F-A5 — font-family must use the documented fallback chain everywhere a
# monospace font is requested.
# ---------------------------------------------------------------------------

def test_fa5_font_chain_hoisted_to_root_svg():
    """The font chain is now set ONCE on the root <svg> as an inherited
    font-family presentation attribute, instead of repeated on every
    <text>. Confirm it lives there exactly once with the documented chain."""
    out = render("deadbeefcafebabe")
    root = _root(out)
    assert root.get("font-family") == FONT_CHAIN, (
        f"root <svg> font-family is not the documented chain: "
        f"{root.get('font-family')!r}"
    )
    # And it must appear exactly once in the whole document (not duplicated
    # onto descendants). lxml escapes the embedded quotes (&quot;) when
    # serializing the attribute, so count a stable unescaped marker token from
    # the chain instead of the raw chain string.
    assert out.count("JetBrains") == 1, (
        f"font chain marker appears {out.count('JetBrains')} times, expected "
        "once (on the root <svg> only)"
    )


def test_fa5_cell_text_inherits_chain_no_per_text_family():
    """Every cell <text> inherits the chain from the root <svg> and carries
    no per-text font-family (neither as a style nor as an attribute)."""
    out = render("deadbeefcafebabe")
    root = _root(out)
    texts = root.findall(".//{http://www.w3.org/2000/svg}text")
    cell_texts = [t for t in texts if t.get("data-color-bar-letter") is None]
    assert cell_texts, "no <text> elements found in rendered SVG"
    for t in cell_texts:
        assert t.get("font-family") is None, (
            f"<text> should inherit font-family, not set it: {t.get('font-family')!r}"
        )
        assert FONT_CHAIN not in (t.get("style") or ""), (
            f"<text> still carries the chain in its style: {t.get('style')!r}"
        )


def test_fa5_color_bar_letters_inherit_chain():
    out = render("deadbeefcafebabe")
    root = _root(out)
    letters = [
        t for t in root.findall(".//{http://www.w3.org/2000/svg}text")
        if t.get("data-color-bar-letter") is not None
    ]
    assert letters, "no color-bar letters found in rendered SVG"
    for t in letters:
        assert t.get("font-family") is None, (
            f"color-bar letter should inherit font-family: {t.get('font-family')!r}"
        )
        assert FONT_CHAIN not in (t.get("style") or "")


def test_fa5_label_strips_inherit_chain():
    """Render input with a suffix (SSH key with comment) so both top and
    bottom label strips are present, then assert each label-strip <text>
    inherits the chain (no per-text font-family)."""
    payload = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGZ user@example"
    out = render(payload)
    root = _root(out)
    ns = "{http://www.w3.org/2000/svg}"
    label_groups = [
        g for g in root.findall(f".//{ns}g")
        if g.get("data-channel") in ("label-top", "label-bottom")
    ]
    assert len(label_groups) >= 1, "expected at least a top label strip"
    saw_text = False
    for g in label_groups:
        for t in g.findall(f"{ns}text"):
            saw_text = True
            assert t.get("font-family") is None, (
                f"label strip <text> should inherit font-family: {t.get('font-family')!r}"
            )
            assert FONT_CHAIN not in (t.get("style") or "")
    assert saw_text, "no <text> elements under label strips"


def test_fa5_bare_monospace_no_longer_present():
    """Defense-in-depth: confirm the previous bare 'monospace' style
    (without the fallback chain) does not appear anywhere in the
    rendered SVG. This guards against a partial fix that updates one
    call site but misses another."""
    out = render("deadbeefcafebabe")
    # The full chain ends in `, monospace`; the bare form would be
    # exactly `font-family: monospace;` with no other names.
    assert "font-family: monospace;" not in out, (
        "found a bare `font-family: monospace;` style — every call "
        "site should use the documented fallback chain"
    )
