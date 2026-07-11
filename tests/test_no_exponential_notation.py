"""R022 (docs/spec.md, "Numeric serialization"): every number an implementation
writes into the SVG MUST be a finite decimal in plain notation — implementations
MUST NOT use exponential/scientific notation (e.g. ``1e-7``), because not every
SVG consumer accepts it in every attribute context and it defeats by-eye diffing.

The obligation is enforced by ``pipeline._compact`` / ``_normalize_numbers``, but
was previously unguarded by a negative-assertion test (surfaced by the v15 spec
editorial requirements inventory, finding N3). This locks it in: no numeric SVG
attribute value may carry a ``<digit>e<±digits>`` token.
"""
import re

from lxml import etree

from entviz.pipeline import (
    render,
    _compact,
    _COORD_ATTRS,
    _COMPOSITE_ATTRS,
)

# The signature of scientific notation: a digit, then e/E, then an optional
# sign and at least one digit. Scoped to numeric attributes only, so a hex
# color like ``#e7be00`` (which lives in fill/stroke, never a numeric attr)
# can never be mistaken for an exponent.
_SCI = re.compile(r"\d[eE][+-]?\d")

# A spread of inputs chosen to exercise the coordinates most at risk of a tiny
# magnitude that a naive formatter would render as ``1e-07``: small grids
# (few-cell) and a large truncated input, plus the ellipse/opacity params.
_INPUTS = [
    "deadbeef",                                    # short hex, small grid
    "123e4567-e89b-12d3-a456-426614174000",        # UUID
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",          # BTC legacy base58check
    "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",  # bech32 segwit
    "G" * 55,                                       # Stellar-ish, base32 body
    "ab" * 200,                                      # 800-byte -> truncated (large-input path)
]


def _numeric_attr_values(root):
    """Yield (element_tag, attr, value) for every numeric SVG attribute that
    ``_normalize_numbers`` is responsible for compacting."""
    for el in root.iter():
        for k, v in el.attrib.items():
            if k in _COORD_ATTRS or k in _COMPOSITE_ATTRS:
                yield el.tag, k, v
            elif k == "style" and "font-size" in v:
                yield el.tag, k, v


def test_rendered_svgs_carry_no_exponential_notation():
    for entropy in _INPUTS:
        root = etree.fromstring(render(entropy).encode())
        for tag, attr, value in _numeric_attr_values(root):
            assert not _SCI.search(value), (
                f"exponential notation in {attr}={value!r} on <{tag}> "
                f"for input {entropy!r} (violates R022)"
            )


def test_compact_never_emits_exponent_for_extreme_magnitudes():
    # Values a naive ``str(float)`` would render in scientific notation.
    for x in (1e-7, -1e-7, 1e-12, 1.5e-9, 1e20, -0.0, 3e-8):
        s = _compact(x)
        assert not _SCI.search(s), f"_compact({x!r}) -> {s!r} carries an exponent"
    # And the specific spec example: a sub-milli-pixel coordinate collapses to 0.
    assert _compact(1e-7) == "0"
    assert _compact(-0.0) == "0"
