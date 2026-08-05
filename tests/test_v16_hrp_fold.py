"""v16: the bech32 HRP is identity-bearing and binds the fingerprint.

Before v16 a bech32 human-readable part was classified as presentation framing
— validated by the polymod, then dropped. Two values sharing a data payload
under different HRPs therefore rendered byte-identically in every channel a
human compares, and differed only in the 12px grey label: a Cosmos address and
its Osmosis spelling, mainnet and testnet Bitcoin or Cardano, and — the case
that motivated the change — a nostr `npub1…` public key and the `nsec1…` secret
key over the same payload.

v16 folds `<hrp>1` into the fingerprint (`prefix ‖ core`), the mechanism DIDs,
URNs, SWHIDs and gitoids already use. See `docs/spec.md` *How identity material
is bound*, `this.i:s3mpr3fx`, and `this.i:hrpb1nd`.
"""
import re

import pytest

from entviz.entropy import parse
from entviz.pipeline import render


# Each pair shares a data payload and differs only in the HRP. The checksums
# differ because the polymod covers the HRP; they are the bound suffix and are
# not part of the core, which is exactly why the fold is needed.
HRP_PAIRS = [
    ("cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e",
     "osmo1qqqsyqcyq5rqwzqfpg9scrgwpugpzysntdz28t"),
    ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
     "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"),
    ("addr1qyqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xmyv4nxw6rfdf4kc"
     "mtwdac8zunnw36hvamc09a8klra0elsr0jfpr",
     "addr_test1qyqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xmyv4nxw6rfdf4kc"
     "mtwdac8zunnw36hvamc09a8klra0els30xwlp"),
    ("npub1802mpadp48s09v7y6hn0wzqe9ga5chtw07qfz23mf3wkuluqjy3swt0n8f",
     "nsec1802mpadp48s09v7y6hn0wzqe9ga5chtw07qfz23mf3wkuluqjy3szayjpu"),
]

# Every attribute below is derived from the fingerprint, so all of them move
# when the hash input changes. Checking the set rather than one of them keeps
# the test honest if a future channel is added or renamed.
_GESTALT_ATTRS = re.compile(
    r'data-(?:surround-bits|edge-color|cell-quartile|cell-blank[a-z-]*|'
    r'ellipse-[a-z-]+|bar-marker-[a-z]+)="[^"]*"')


def _gestalt(entropy: str) -> list[str]:
    return _GESTALT_ATTRS.findall(render(entropy))


@pytest.mark.parametrize("a,b", HRP_PAIRS)
def test_same_payload_different_hrp_shares_a_core(a, b):
    # The premise of the whole test: the cores really are identical, so nothing
    # except the fold can distinguish these two values. If a future parser
    # change puts the HRP or the checksum into the core, this assertion fails
    # and the pair stops testing what it was written to test.
    pa, pb = parse(a), parse(b)
    assert pa.core == pb.core
    assert pa.prefix != pb.prefix
    assert pa.prefix_semantic and pb.prefix_semantic


@pytest.mark.parametrize("a,b", HRP_PAIRS)
def test_same_payload_different_hrp_renders_differently(a, b):
    assert _gestalt(a) != _gestalt(b)


@pytest.mark.parametrize("a,b", HRP_PAIRS)
def test_the_two_renders_are_not_merely_label_deep(a, b):
    # A reader who never looks at the label must still see a difference, so the
    # divergence has to reach the cells' own painted attributes — not just the
    # ellipse or the colour bar at the edges of the picture.
    cells_a = re.findall(r'data-surround-bits="[^"]*"', render(a))
    cells_b = re.findall(r'data-surround-bits="[^"]*"', render(b))
    assert cells_a and cells_b
    assert cells_a != cells_b


def test_hrp_is_still_readable_in_the_label():
    # The fold puts the HRP in the fingerprint, not in the cells, so the label
    # is the only text carrier left. Losing it there would leave a read-aloud
    # comparison with no way to tell these values apart at all.
    from entviz.characterize import characterize, render_label
    for entropy, expected in (
        ("cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e", "bech32, cosmos1"),
        ("osmo1qqqsyqcyq5rqwzqfpg9scrgwpugpzysntdz28t", "bech32, osmo1"),
        # v17 added the `testnet` mod here. When this vector was written for
        # v16 it read `BTC, tb1` — a testnet address labeled exactly like its
        # mainnet twin, because the network qualifier was hardcoded to mainnet.
        # See test_v17_network_qualifier.py and `this.i:n3twrkq`.
        ("tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx", "BTC, testnet, tb1"),
    ):
        assert render_label(characterize(entropy))[0] == expected


def test_bech32_checksum_is_the_suffix_on_every_path():
    # v16 made this uniform: before, the generic and Cardano parsers split the
    # checksum off while the Bitcoin-segwit and Litecoin parsers left it in the
    # core — which bound their HRP by accident and inflated size_bits.
    for entropy in ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
                    "ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n9",
                    "cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e"):
        p = parse(entropy)
        assert p.suffix is not None and len(p.suffix) == 6, entropy
        assert entropy.endswith(p.suffix), entropy
        assert not p.core.endswith(p.suffix), entropy


def test_cashaddr_is_the_documented_exception():
    # CashAddr is deliberately NOT folded: its prefix is optional, so a bare
    # body and its prefixed spelling are the same address and must not diverge.
    # It is safe unfolded because its checksum stays in the core and covers the
    # prefix. See parse_bitcoin_cash_address and tick 4dua.
    bare = parse("qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a")
    prefixed = parse("bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a")
    assert bare.core == prefixed.core
    assert not bare.prefix_semantic
    assert _gestalt("qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a") == _gestalt(
        "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a")
