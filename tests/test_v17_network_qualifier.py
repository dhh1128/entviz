"""v17: the network qualifier is read from the prefix, not assumed.

Through v16 `characterize()` hardcoded `network: "mainnet"` for every BTC
address and emitted no network at all for Cardano Shelley. Because `_mods()`
surfaces the network only when it *departs* from mainnet (the v14 rule —
"testnet loud, mainnet silent"), a testnet address rendered a label
indistinguishable from its mainnet twin: `BTC, tb1` where `BTC, testnet, tb1`
was required. The reference was non-conformant to its own spec, in the same
mainnet-versus-testnet confusability family that v16 closed for the HRP.

The Shelley matcher also had a length hole, found while writing these tests: its
body floor of 50 characters excluded every 29-byte Shelley address — all reward
(`stake1…`) and enterprise addresses, which are 47 characters ahead of the
6-character checksum. See `this.i:n3twrkq` and `this.i:sh3lley29`.
"""
import pytest

from entviz.characterize import characterize, render_label
from entviz.entropy import parse


def _q(value):
    return characterize(value)["qualifiers"]


def _label(value):
    return render_label(characterize(value))[0]


# (value, expected network, expected label)
NETWORK_CASES = [
    ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "mainnet", "BTC, bc1"),
    ("tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx", "testnet", "BTC, testnet, tb1"),
    ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "mainnet", "BTC, 1"),
    ("mfWyW5fc9NUj75YAnFgoRLrjxgLDn2MMth", "testnet", "BTC, testnet, m"),
    ("ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n9", "mainnet", "LTC, ltc1"),
    ("bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a", "mainnet",
     "BCH, bitcoincash:"),
    ("bchtest:qpm2qsznhks23z7629mms6s4cwef74vcwvqcw003ap", "testnet",
     "BCH, testnet, bchtest:"),
    ("stake1uyqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xcwfvml6", "mainnet",
     "ADA, stake1"),
    ("stake_test1uqqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xcfrxem8", "testnet",
     "ADA, testnet, stake_test1"),
]


@pytest.mark.parametrize("value,network,label", NETWORK_CASES)
def test_network_is_read_from_the_prefix(value, network, label):
    assert _q(value).get("network") == network, value
    assert _label(value) == label, value


@pytest.mark.parametrize("value,network,label", NETWORK_CASES)
def test_testnet_is_loud_and_mainnet_is_silent(value, network, label):
    # The v14 label rule, restated as a property so it cannot rot: the word
    # appears in the label exactly when the network departs from mainnet.
    assert ("testnet" in label) == (network == "testnet"), value


def test_a_testnet_address_never_labels_like_its_mainnet_twin():
    # The defect, stated directly. These two share a payload and differ only in
    # the network; before v17 both read "BTC, ...", separable only by the small
    # prefix slot, and their characterizations were byte-identical.
    main = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
    test = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"
    assert parse(main).core == parse(test).core, "premise: one payload"
    assert _q(main) != _q(test)
    assert _label(main) != _label(test)


def test_byron_claims_no_network():
    # Deliberate: a Byron address's network magic is inside the CBOR payload,
    # which this parser does not decode — the same reason its CRC-32 goes
    # unverified. Asserting mainnet would be a guess dressed as a fact.
    for value in (
        "Ae2tdPwUPEZ7SZaSCeU8sGZXGZ7YrVc96FnzYdZcLkbry4CqUKax9dNeEoe",
        "DdzFFzCqrht1D2Tv5F9HLtZHEd4P9Tddf9DFv3d4KXa2RxudcL4uHKWtc2HfiDopch5UHyZkXQx7",
    ):
        ch = characterize(value)
        assert ch["scheme"] == "ada"
        assert ch["qualifiers"] == {"variant": "byron"}
        assert "testnet" not in render_label(ch)[0]


# --- the Shelley 29-byte hole -------------------------------------------------

SHELLEY_29_BYTE = [
    "stake1uyqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xcwfvml6",
    "stake_test1uqqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xcfrxem8",
]


@pytest.mark.parametrize("value", SHELLEY_29_BYTE)
def test_29_byte_shelley_addresses_reach_the_cardano_parser(value):
    # Before v17 the mainnet form fell through to the generic bech32 parser
    # (scheme "bech32"), and the testnet form did not parse as bech32 at all —
    # `stake_test` contains `_`, outside the generic parser's [a-z] HRP charset,
    # so it landed on the base64url fallback with no scheme and no checksum
    # verification. Both are 47 body characters, under the old floor of 50.
    p = parse(value)
    assert p is not None
    assert p.type == "ADA Shelley", value
    assert p.prefix_semantic is True
    assert characterize(value)["scheme"] == "ada"


def test_the_57_byte_base_address_still_parses():
    # The floor moved from 50 to 45; the long form must be unaffected.
    value = ("addr1qyqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xmyv4nxw6rfdf4kc"
             "mtwdac8zunnw36hvamc09a8klra0elsr0jfpr")
    assert parse(value).type == "ADA Shelley"
