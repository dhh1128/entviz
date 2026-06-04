"""
Additional address formats: Stellar muxed accounts and generic
checksum-validated bech32 (Cosmos-SDK chains). See `this.i:xtra4lph`.

(Solana, JWK, NanoID, z-base-32, and base62 were deliberately DEFERRED —
see the same this.i node for why each is ambiguous, would mislabel a large
fraction of base64 inputs, or needs a larger design decision.)
"""
from entviz.entropy import (
    parse, parse_bech32_address, BASE32, BECH32,
)


# ---- Stellar muxed (M…) ------------------------------------------------

# SEP-23 muxed-account example (69 chars).
MUXED = "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVAAAAAAAAAAAAAJLK"


def test_stellar_muxed_parses():
    p = parse(MUXED)
    assert p.type == "XLM muxed"
    assert p.alphabet is BASE32
    assert p.prefix == "M"
    assert p.core == MUXED[1:].upper()


def test_stellar_plain_g_still_xlm():
    g = "GCKFBEIYTKP5RDBQMUTAPDCDHF2TR4LPNRGW4JBQQTQUYZP4LDKP3SGM"
    assert parse(g).type == "XLM"


# ---- Generic bech32 (Cosmos-SDK chains) --------------------------------

COSMOS = "cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e"
OSMO = "osmo1qqqsyqcyq5rqwzqfpg9scrgwpugpzysntdz28t"
JUNO = "juno1zs23v9ccrydpk8qarc0jqgfzyvjz2f38fjf3ru"


def test_cosmos_address_parses_with_hrp_label():
    p = parse(COSMOS)
    assert p.type == "bech32 cosmos"
    assert p.alphabet is BECH32
    assert p.prefix == "cosmos1"
    assert p.suffix == COSMOS.split("1", 1)[1][-6:]   # 6-char checksum
    assert p.core == COSMOS.split("1", 1)[1][:-6]


def test_hrp_names_the_chain_generically():
    assert parse(OSMO).type == "bech32 osmo"
    assert parse(JUNO).type == "bech32 juno"


def test_invalid_checksum_is_rejected():
    bad = COSMOS[:-1] + ("q" if COSMOS[-1] != "q" else "p")
    assert parse_bech32_address(bad) is None


def test_specific_bech32_formats_still_win():
    # Bitcoin segwit / Cardano have dedicated parsers that must run first,
    # not be swallowed by the generic bech32 parser.
    assert parse("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4").type != "bech32 bc"
