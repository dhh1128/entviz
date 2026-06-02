import pytest

from entviz.fingerprint import Ftok, compute_fingerprint, tokenize_fingerprint


def test_fingerprint_is_64_bytes():
    assert len(compute_fingerprint("anything")) == 64


def test_fingerprint_deterministic():
    assert compute_fingerprint("DEADBEEF") == compute_fingerprint("DEADBEEF")


def test_fingerprint_differs_for_different_inputs():
    assert compute_fingerprint("DEADBEEF") != compute_fingerprint("DEADBEEE")


def test_fingerprint_matches_known_sha512_vector():
    # SHA-512("abc") — canonical NIST test vector.
    expected = bytes.fromhex(
        "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a"
        "2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f"
    )
    assert compute_fingerprint("abc") == expected


def test_fingerprint_single_bit_flip_avalanches():
    # SHA-512 should change roughly half its bits when one input bit flips.
    a = compute_fingerprint("550e8400e29b41d4a716446655440000")
    b = compute_fingerprint("550e8400e29b41d4a716446655440001")
    diff_bits = sum(bin(x ^ y).count("1") for x, y in zip(a, b))
    # 512 bits total; ~256 expected. 200 is a generous lower bound.
    assert diff_bits > 200


def test_tokenize_fingerprint_yields_22_ftoks():
    digest = compute_fingerprint("anything")
    assert len(tokenize_fingerprint(digest)) == 22


def test_tokenize_fingerprint_indices_are_0_to_21():
    ftoks = tokenize_fingerprint(compute_fingerprint("x"))
    assert [f.index for f in ftoks] == list(range(22))


def test_tokenize_fingerprint_quants_are_24_bit():
    ftoks = tokenize_fingerprint(compute_fingerprint("x"))
    for f in ftoks:
        assert 0 <= f.quant < (1 << 24)


def test_tokenize_fingerprint_rejects_wrong_length():
    with pytest.raises(ValueError):
        tokenize_fingerprint(b"\x00" * 63)
    with pytest.raises(ValueError):
        tokenize_fingerprint(b"\x00" * 65)


def test_partial_ftok_from_zero_digest():
    # All-zero digest: base64url encodes to 21 × "AAAA" + "AA" (the trailing
    # byte yields 2 base64 chars). Verifies the partial ftok is shaped correctly
    # and its quant is 0 when no bits are set.
    digest = b"\x00" * 64
    ftoks = tokenize_fingerprint(digest)
    for i in range(21):
        assert ftoks[i].text == "AAAA"
        assert ftoks[i].quant == 0
    assert ftoks[21].text == "AA"
    assert ftoks[21].quant == 0


def test_partial_ftok_extends_low_order_bits():
    # 63 zero bytes + one 0xFF byte. The 0xFF encodes to base64url as "_w":
    # 0xFF padded with 4 trailing zero bits = 0xFF0 (12 bits), split into
    # 6+6 = 0b111111 (63 → '_') and 0b110000 (48 → 'w').
    # The v1 tokenize() routine then extends those 12 bits to 24 by repeating
    # the low-order bits: quant = (0xFF0 << 12) | 0xFF0 = 0xFF0FF0.
    digest = b"\x00" * 63 + b"\xff"
    ftoks = tokenize_fingerprint(digest)
    assert ftoks[21].text == "_w"
    assert ftoks[21].quant == 0xFF0FF0


def test_ftok_avalanche_across_ftoks():
    # A single-bit input change should change most of the 22 ftoks, because
    # SHA-512 avalanche scrambles all 64 digest bytes.
    a = tokenize_fingerprint(compute_fingerprint("550e8400e29b41d4a716446655440000"))
    b = tokenize_fingerprint(compute_fingerprint("550e8400e29b41d4a716446655440001"))
    differing = sum(1 for x, y in zip(a, b) if x.quant != y.quant)
    assert differing >= 20  # 22 total; allow a tiny margin for collisions


def test_ftok_is_distinct_type_from_token():
    # Ftok must not be Token — keeps the type system honest about which
    # data source a value came from.
    from entviz.entropy import Token
    ftok = tokenize_fingerprint(compute_fingerprint("x"))[0]
    assert isinstance(ftok, Ftok)
    assert not isinstance(ftok, Token) or Ftok is not Token
