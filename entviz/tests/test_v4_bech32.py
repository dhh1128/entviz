"""
v4 bech32 alphabet: 5 bits per character, token length = 4 chars (= 20 bits).
20-bit tokens are extended to 24 bits via the existing low-order-bit repeat
rule. Used by Bitcoin SegWit, Litecoin (ltc1...), Cardano Shelley, etc.
"""
from entviz.entropy import (
    parse, tokenize_entropy,
    BECH32, BECH32_ALPHABET, HEX, BASE58, BASE64, BASE64URL,
)


# ---- alphabet object ---------------------------------------------------


def test_bech32_alphabet_exists():
    assert BECH32 is not None
    assert BECH32.name == "bech32"


def test_bech32_alphabet_is_5_bits_per_char():
    assert BECH32.bits_per_char == 5


def test_bech32_alphabet_chars_are_32():
    """Bech32 character set per BIP-173: qpzry9x8gf2tvdw0s3jn54khce6mua7l."""
    assert len(BECH32_ALPHABET) == 32
    # Standard bech32 alphabet from BIP-173, lowercase
    assert BECH32_ALPHABET == "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def test_bech32_alphabet_excludes_ambiguous_chars():
    """Bech32 excludes '1', 'b', 'i', 'o' to reduce ambiguity (1 is also
    the prefix separator)."""
    assert '1' not in BECH32_ALPHABET
    assert 'b' not in BECH32_ALPHABET
    assert 'i' not in BECH32_ALPHABET
    assert 'o' not in BECH32_ALPHABET


# ---- tokenization ------------------------------------------------------


def test_bech32_token_length_is_4_chars():
    """4 chars × 5 bits = 20 bits per token; extended to 24 by the spec rule.
    The alternate (5 chars = 25 bits) would overshoot the 24-bit quant
    budget by 1 bit."""
    text = "qpzry9x8gf"  # 10 bech32 chars → 2 full 4-char tokens + 1 partial 2-char
    tokens, truncated = tokenize_entropy(text, BECH32)
    assert not truncated
    assert len(tokens) == 3
    assert tokens[0].text == "qpzr"
    assert tokens[1].text == "y9x8"
    assert tokens[2].text == "gf"


def test_bech32_full_token_quant_is_extended_from_20_to_24_bits():
    """A 4-char bech32 token represents 20 bits; the quant extension rule
    pads up to 24 bits by appending low-order bits."""
    # "qpzr" in bech32 → q=0, p=1, z=2, r=3 → 20-bit value:
    #   (0 << 15) | (1 << 10) | (2 << 5) | 3 = 0x443
    # Extension: shift = min(20, 4) = 4 →
    #   pad = quant & 0xF = 0x3
    #   quant = (0x443 << 4) | 0x3 = 0x4433
    tokens, _ = tokenize_entropy("qpzr", BECH32)
    assert len(tokens) == 1
    assert tokens[0].quant == 0x4433


def test_bech32_partial_token_extends_normally():
    """A partial bech32 token (1-3 chars) extends to 24 bits via the
    standard repeat-low-order-bits rule."""
    # 2 chars "qp" → q=0, p=1 → 10 bits 0b00000_00001 = 0x001
    # Extension chain: shift=10 → quant = (0x001 << 10) | 0x001 = 0x00401, bits=20
    # → shift=4 → quant = (0x00401 << 4) | 0x1 = 0x04011
    tokens, _ = tokenize_entropy("qp", BECH32)
    assert tokens[0].quant == 0x04011


# ---- parser integration ------------------------------------------------


def test_bitcoin_segwit_parses_as_bech32():
    """A real Bitcoin SegWit P2WPKH address (BIP-173 test vector) should
    parse with the BECH32 alphabet, not fall through to base64."""
    # BIP-173 test vector
    addr = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
    p = parse(addr)
    assert p is not None
    assert p.type == "BTC SegWit"
    assert p.alphabet is BECH32
    # Core = address minus the "bc1" prefix
    assert p.core == "qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"


def test_bitcoin_segwit_p2wsh_parses():
    """P2WSH addresses are longer (62 chars) but use the same alphabet."""
    addr = "bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3"
    p = parse(addr)
    assert p is not None
    assert p.type == "BTC SegWit"
    assert p.alphabet is BECH32


def test_cardano_shelley_parses_as_bech32():
    """Cardano Shelley addresses use bech32."""
    # A real Cardano Shelley mainnet address
    addr = "addr1q9c0sj9wp29txqlt0qkc4cz76d5szl4xqgmgpw70ay9zkmskq7stm5kkjjjvrjz9p3kgxx0plzkphkn2yepg6w2zjphshtm0rl"
    p = parse(addr)
    assert p is not None
    assert p.type == "ADA Shelley"
    assert p.alphabet is BECH32


def test_litecoin_modern_parses_as_bech32():
    """Modern Litecoin ltc1... addresses use bech32."""
    addr = "ltc1qhw6dgkk52v9eqzukju7vrqpw0jt4wll6e6n4q5"
    p = parse(addr)
    assert p is not None
    assert p.alphabet is BECH32


def test_render_a_bech32_address_does_not_crash():
    """End-to-end: rendering a bech32 address should produce a valid SVG."""
    from entviz.pipeline import render
    svg = render("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
    assert svg.startswith("<svg")
    assert "</svg>" in svg


def test_long_bech32_input_truncates_to_22_tokens_or_fewer():
    """For long bech32 inputs (e.g. a Cardano Shelley address > 512 bits),
    the >512-bit truncation rule must keep token_count ≤ 22. The naive
    "ceil(256/bits_per_char) chars per side" formula yields 52 chars × 2 =
    13 tokens × 2 = 26 tokens for bech32, exceeding the cap. The fix is
    to also bound chars_per_side by 11 · token_len = 44 chars per side
    so each side stays at ≤ 11 tokens."""
    # A long bech32 input — 92 bech32 chars × 5 bits = 460 bits, but the
    # 22-token cap should still apply because 92/4 > 22 tokens.
    long_bech32 = "q9c0sj9wp29txqlt0qkc4cz76d5szl4xqgmgpw70ay9zkmskq7stm5kkjjjvrjz9p3kgxx0plzkphkn2yepg6w2zjphs"
    tokens, truncated = tokenize_entropy(long_bech32, BECH32)
    assert truncated
    assert len(tokens) <= 22


def test_long_bech32_address_renders_without_error():
    """Regression test for the Cardano Shelley case that was crashing
    with IndexError because tokenize_entropy emitted 26 tokens."""
    from entviz.pipeline import render
    addr = "addr1q9c0sj9wp29txqlt0qkc4cz76d5szl4xqgmgpw70ay9zkmskq7stm5kkjjjvrjz9p3kgxx0plzkphkn2yepg6w2zjphshtm0rl"
    svg = render(addr)
    assert svg.startswith("<svg")
