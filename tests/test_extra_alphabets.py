"""
Additional address formats: Stellar muxed accounts and generic
checksum-validated bech32 (Cosmos-SDK chains). See `this.i:xtra4lph`.

(Solana, JWK, NanoID, z-base-32, and base62 were deliberately DEFERRED —
see the same this.i node for why each is ambiguous, would mislabel a large
fraction of base64 inputs, or needs a larger design decision.)
"""
import pytest

from entviz.entropy import (
    parse, parse_bech32_address, BASE32, BECH32, Bech32ChecksumError,
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


def test_cosmos_address_parses_with_hrp_in_prefix():
    p = parse(COSMOS)
    assert p.type == "bech32"          # chain name lives in the prefix, not the type
    assert p.alphabet is BECH32
    assert p.prefix == "cosmos1"
    assert p.suffix == COSMOS.split("1", 1)[1][-6:]   # 6-char checksum
    assert p.core == COSMOS.split("1", 1)[1][:-6]


def test_hrp_names_the_chain_generically():
    # The chain is named by the (displayed) prefix, generically, without a
    # hard-coded chain list; the type stays the bare alphabet.
    for addr, hrp in ((OSMO, "osmo1"), (JUNO, "juno1")):
        p = parse(addr)
        assert p.type == "bech32"
        assert p.prefix == hrp


def test_invalid_checksum_falls_through_rather_than_rejecting():
    # v17 correction, reversing the v14 rule ON THIS PATH ONLY. v14 rejected a
    # `<hrp>1<data>` match with a bad polymod, reasoning that the shape was "a
    # clear bech32 structural match". It is not: measured, ~1.1% of random short
    # hex strings matched the old 8-character-data form by accident and were
    # refused outright. With no registry of valid HRPs, a failing checksum here
    # means only "not bech32 after all", so the parser declines and the input
    # continues down the chain. The NAMED schemes (bc1/tb1, ltc1, addr1,
    # bitcoincash:) still reject — see test_v14_label_and_checksums.py.
    bad = COSMOS[:-1] + ("q" if COSMOS[-1] != "q" else "p")
    assert parse_bech32_address(bad) is None
    # ...and the whole-parser path renders it as a bare encoding, never AS an
    # address: the label says what was actually recognized.
    assert parse(bad).type != "bech32"


def test_specific_bech32_formats_still_win():
    # Bitcoin segwit / Cardano have dedicated parsers that must run first,
    # not be swallowed by the generic bech32 parser.
    assert parse("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4").type != "bech32 bc"
