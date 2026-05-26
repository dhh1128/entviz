"""
v4 hex normalization: plain hex (via parse_hex) is normalized to
lowercase, matching UUIDs (which already lowercase). This avoids
the oral-reading ambiguity where uppercase A-F would be pronounced
"cap A" through "cap F".

Ethereum addresses are exempt — they preserve EIP-55 mixed case as
a checksum signal.
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


def test_ethereum_preserves_eip55_mixed_case():
    """Ethereum core preserves EIP-55 checksum case (mixed case meaningful)."""
    p = parse("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
    assert p is not None
    assert p.type == "Ethereum"
    # The full 40-char body is in `core`, normalized to EIP-55 mixed case.
    has_upper = any(c.isupper() for c in p.core if c.isalpha())
    has_lower = any(c.islower() for c in p.core if c.isalpha())
    assert has_upper and has_lower


def test_rendered_hex_cells_use_lowercase():
    """The cell text in a rendered hex entviz should be lowercase."""
    svg = render("a1b2c3d4e5f6a7b8")
    doc = etree.fromstring(svg.encode())
    texts = [t.text for t in doc.xpath('//*[local-name()="text"]')
             if t.get("text-anchor") == "middle" and t.text]
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
    texts = [t.text for t in doc.xpath('//*[local-name()="text"]')
             if t.get("text-anchor") == "middle" and t.text]
    for t in texts:
        for c in t:
            if c.isalpha():
                assert c.islower(), f"got uppercase letter {c!r} in cell text {t!r}"
