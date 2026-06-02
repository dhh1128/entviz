"""
F7b: lenient EIP-55 case validation for Ethereum addresses.

Spec reference: docs/spec.md, "Ethereum (EIP-55) case validation" paragraph.
Decision rationale: this.i:3ip55rj1.

Lenient B1 rule:
  - All-lowercase 40-hex with 0x prefix: accept ("checksum not asserted").
  - All-uppercase 40-hex with 0x prefix: accept ("checksum not asserted").
  - Mixed-case 40-hex with 0x prefix AND matches EIP-55 canonical case: accept.
  - Mixed-case 40-hex with 0x prefix AND does NOT match EIP-55: REJECT with
    EIP55ChecksumError identifying the first mismatched-case position.

In all accepted cases, the parsed core is the lowercase 40-hex body — entviz
does NOT silently re-derive the canonical case (the v4 bug this finding fixed:
re-deriving meant an invalid-checksum input rendered identically to a valid
one, eating the checksum signal).
"""
import pytest

from entviz.entropy import (
    EIP55ChecksumError,
    parse,
    parse_ethereum_address,
)
from entviz.keccak import keccak256
from entviz.pipeline import render


# A known-canonical EIP-55 vector from the spec.
SPEC_VECTOR_MIXED = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
SPEC_VECTOR_LOWER = "0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed"
SPEC_VECTOR_UPPER = "0X5AAEB6053F3E94C9B9A09F33669435E7EF1BEAED"


# ---------------------------------------------------------------------------
# Keccak-256 vector tests — defend future implementers against the
# sha3_256/keccak256 confusion (NIST SHA3-256 has different padding and
# would silently give wrong-but-non-crashing results).
# ---------------------------------------------------------------------------

def test_keccak256_empty_input():
    """RFC test vector: keccak256(b'') has a known digest."""
    assert keccak256(b'').hex() == (
        "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    )


def test_keccak256_abc():
    """keccak256(b'abc') has a known digest, distinct from SHA3-256(b'abc')."""
    assert keccak256(b'abc').hex() == (
        "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"
    )


def test_keccak256_vectors_eip55():
    """The EIP-55 spec's published canonical addresses should re-derive
    correctly from their lowercase forms via our keccak256."""
    # Each pair: (lowercase 40-hex, canonical EIP-55 mixed-case).
    pairs = [
        ("5aaeb6053f3e94c9b9a09f33669435e7ef1beaed",
         "5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"),
        ("fb6916095ca1df60bb79ce92ce3ea74c37c5d359",
         "fB6916095ca1df60bB79Ce92cE3Ea74c37c5d359"),
        ("dbf03b407c01e7cd3cbea99509d93f8dddc8c6fb",
         "dbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB"),
    ]
    for lower, canonical in pairs:
        h = keccak256(lower.encode('ascii')).hex()
        out = []
        for i, c in enumerate(lower):
            if c.isdigit():
                out.append(c)
            elif int(h[i], 16) >= 8:
                out.append(c.upper())
            else:
                out.append(c.lower())
        assert ''.join(out) == canonical, (
            f"keccak-derived canonical for {lower} did not match spec vector"
        )


# ---------------------------------------------------------------------------
# Lenient B1 classification: all-lower, all-upper, mixed-valid, mixed-invalid.
# ---------------------------------------------------------------------------

def test_all_lower_accepts_and_normalizes():
    """All-lowercase Ethereum input → accepted, core is lowercase."""
    p = parse(SPEC_VECTOR_LOWER)
    assert p is not None
    assert p.type == "ETH"
    assert p.prefix == "0x"
    # Per lenient B1: core is the normalized (lowercase) 40-hex body.
    assert p.core == SPEC_VECTOR_LOWER[2:]
    assert p.core.islower() or all(c.isdigit() or c.islower() for c in p.core)


def test_all_upper_accepts_and_normalizes_to_lower():
    """All-uppercase Ethereum input → accepted, core normalized to lowercase
    (so the visualization is consistent with the all-lower form)."""
    p = parse(SPEC_VECTOR_UPPER)
    assert p is not None
    assert p.type == "ETH"
    # Core normalized to lowercase per lenient B1.
    assert p.core == SPEC_VECTOR_LOWER[2:]


def test_all_lower_and_all_upper_render_identically():
    """All-lower and all-upper of the same address must render byte-identical
    SVG — they normalize to the same lowercase core, so every downstream
    channel (text, fingerprint, color bar, …) sees the same bytes."""
    svg_lower = render(SPEC_VECTOR_LOWER)
    svg_upper = render(SPEC_VECTOR_UPPER)
    assert svg_lower == svg_upper


def test_mixed_case_valid_eip55_accepts():
    """The spec's canonical EIP-55 vector → accepted, core normalized to lowercase."""
    p = parse(SPEC_VECTOR_MIXED)
    assert p is not None
    assert p.type == "ETH"
    # Per lenient B1: even mixed-case-valid normalizes the core to lowercase
    # (the checksum has been validated; the canonical case need not be carried
    # into the visualization).
    assert p.core == SPEC_VECTOR_LOWER[2:]


def test_mixed_case_valid_renders_identically_to_all_lower():
    """Mixed-case-valid and all-lower must produce the same SVG, since both
    normalize to the same lowercase core."""
    svg_mixed = render(SPEC_VECTOR_MIXED)
    svg_lower = render(SPEC_VECTOR_LOWER)
    assert svg_mixed == svg_lower


def test_mixed_case_invalid_eip55_raises():
    """Mutate one hex letter's case in the spec vector → rejected with
    EIP55ChecksumError identifying the first mismatched position."""
    # Spec vector:  0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed
    # Position 2 in the body is 'A' (canonical upper). Flip it to lower 'a'.
    # The body is everything after "0x".
    body = list(SPEC_VECTOR_MIXED[2:])
    # Find the first uppercase letter and flip it.
    flip_idx = next(i for i, c in enumerate(body) if c.isupper())
    body[flip_idx] = body[flip_idx].lower()
    bad = "0x" + ''.join(body)

    with pytest.raises(EIP55ChecksumError) as exc:
        parse(bad)
    msg = str(exc.value)
    # The exception message must identify the position (0-based into the body).
    assert str(flip_idx) in msg, (
        f"expected position {flip_idx} in error message, got: {msg!r}"
    )
    # And the input address should be in the message so the user can fix it.
    assert bad in msg or bad.lower() in msg.lower()


def test_eip55_checksum_error_is_value_error():
    """EIP55ChecksumError must subclass ValueError so existing handlers
    that catch ValueError continue to work."""
    assert issubclass(EIP55ChecksumError, ValueError)


def test_all_lower_with_no_eip55_canonical_match_not_rejected():
    """REGRESSION for the strict-B1 trap: an all-lowercase 0x-prefixed
    Ethereum input whose case pattern does NOT match the EIP-55 canonical
    case MUST NOT be rejected. The whole point of lenient B1 is that
    all-lower inputs are 'checksum not asserted' and accepted unchanged."""
    # SPEC_VECTOR_LOWER's canonical case has at least one uppercase letter,
    # so the all-lower form by definition does NOT match canonical case.
    # Sanity-check that fact (otherwise this test is vacuous).
    h = keccak256(SPEC_VECTOR_LOWER[2:].encode('ascii')).hex()
    has_canonical_upper = any(
        c.isalpha() and int(h[i], 16) >= 8
        for i, c in enumerate(SPEC_VECTOR_LOWER[2:])
    )
    assert has_canonical_upper, "test vector lost its canonical-upper letters"
    # Now confirm parse accepts the all-lower form anyway.
    p = parse(SPEC_VECTOR_LOWER)
    assert p is not None
    assert p.type == "ETH"


def test_mixed_invalid_does_not_silently_fall_through_to_hex():
    """F7b regression: a mixed-case-invalid Ethereum input MUST raise rather
    than silently fall through to parse_hex (which would lowercase the body
    and produce a Parsed(type='hex', ...) — exactly the silent-normalization
    attack F7b documents)."""
    body = list(SPEC_VECTOR_MIXED[2:])
    flip_idx = next(i for i, c in enumerate(body) if c.isupper())
    body[flip_idx] = body[flip_idx].lower()
    bad = "0x" + ''.join(body)

    with pytest.raises(EIP55ChecksumError):
        parse(bad)
    # Also verify: parse_ethereum_address itself raises (it doesn't return None
    # to let parse_hex have a turn, because the input IS Ethereum-shaped with
    # an explicit 0x prefix — silent fall-through is the bug we're closing).
    with pytest.raises(EIP55ChecksumError):
        parse_ethereum_address(bad)


def test_non_ethereum_shape_still_returns_none():
    """parse_ethereum_address must continue to return None for inputs that
    don't match the Ethereum prefix-and-shape — the next parser gets a turn."""
    # Wrong length (39 hex):
    assert parse_ethereum_address("0x" + "a" * 39) is None
    # Non-hex character:
    assert parse_ethereum_address("0x" + "g" * 40) is None


def test_renders_dont_crash_for_all_three_accepted_cases():
    """End-to-end smoke: each accepted case renders to a non-empty SVG."""
    for inp in (SPEC_VECTOR_LOWER, SPEC_VECTOR_UPPER, SPEC_VECTOR_MIXED):
        svg = render(inp)
        assert svg
        assert svg.lstrip().startswith("<")
