"""
v4 hex normalization: plain hex (via parse_hex) is normalized to
lowercase, matching UUIDs (which already lowercase). This avoids
the oral-reading ambiguity where uppercase A-F would be pronounced
"cap A" through "cap F".

v5 update (F7b / lenient EIP-55): Ethereum addresses are ALSO
normalized to lowercase in the core. The checksum is validated at
parse time (mixed-case-invalid raises EIP55ChecksumError; see
test_f7_eip55.py), then the canonical case is discarded for
visualization purposes. Pre-v5 the parser silently re-derived
canonical case, which made an invalid-checksum input render
identically to a valid one (review F7).
"""
from entviz.entropy import parse
from entviz.pipeline import render
from lxml import etree


def test_plain_hex_normalized_to_lowercase():
    """A plain hex input via parse_hex is stored lowercase."""
    p = parse("DEADBEEF12345678")
    assert p is not None
    assert p.type == "hex"
    assert p.core == "deadbeef12345678"


def test_plain_hex_already_lowercase_stays_lowercase():
    p = parse("a1b2c3d4e5f6a7b8")
    assert p is not None
    assert p.core == "a1b2c3d4e5f6a7b8"


def test_uuid_stays_lowercase():
    """UUID parser already lowercases; verify unchanged."""
    p = parse("550E8400-E29B-41D4-A716-446655440000")
    assert p is not None
    assert p.core == "550e8400e29b41d4a716446655440000"


def test_ethereum_normalizes_to_lowercase_after_eip55_validation():
    """v5 lenient B1: Ethereum core is normalized to lowercase in every
    accepted case. The EIP-55 checksum (when present) has already been
    validated at parse time; carrying canonical case into the visualization
    was the F7b silent-normalization bug."""
    # Input is a known-valid EIP-55 mixed-case address.
    p = parse("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
    assert p is not None
    assert p.type == "ETH"
    # The full 40-char body is in `core`, normalized to lowercase.
    assert p.core == "742d35cc6634c0532925a3b844bc454e4438f44e"
    assert all(c.isdigit() or c.islower() for c in p.core)


def test_rendered_hex_cells_use_lowercase():
    """The cell text in a rendered hex entviz should be lowercase."""
    svg = render("a1b2c3d4e5f6a7b8")
    doc = etree.fromstring(svg.encode())
    # v5: color-bar band letters are uppercase by design; exclude them.
    texts = [t.text for t in doc.xpath('//*[local-name()="text"]')
             if t.get("text-anchor") == "middle" and t.text
             and t.get("data-color-bar-letter") != "true"]
    assert texts, "no cell text found"
    for t in texts:
        # Letters in cell text should all be lowercase.
        for c in t:
            if c.isalpha():
                assert c.islower(), f"got uppercase letter {c!r} in cell text {t!r}"


def test_rendered_uppercase_hex_input_displays_lowercase():
    """Even if user enters DEADBEEF (uppercase), the cells display
    lowercase after normalization."""
    svg = render("DEADBEEFCAFEBABE")
    doc = etree.fromstring(svg.encode())
    # v5: color-bar band letters are uppercase by design; exclude them.
    texts = [t.text for t in doc.xpath('//*[local-name()="text"]')
             if t.get("text-anchor") == "middle" and t.text
             and t.get("data-color-bar-letter") != "true"]
    for t in texts:
        for c in t:
            if c.isalpha():
                assert c.islower(), f"got uppercase letter {c!r} in cell text {t!r}"
