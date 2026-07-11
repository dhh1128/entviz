"""v15: the top label echoes the stripped FRONT prefix as a trailing slot, so a
reader can reconcile the value they pasted against the cells (whose first
character is otherwise silently different — the prefix was peeled off the front
before visualization). This mirrors the bottom strip, which already reconciles
the END of the value via ``...<suffix>``.

Design decisions locked in the 2026-07-10 session (see docs/spec.md ->
"Label strips" and this.i:v15pfxlbl):

  * Every scheme whose front prefix is *stripped* (a ``bind="none"`` leading
    part: ``0x``, ``bc1``, ``cosmos1``, Stellar ``G``, the SSH header, …) shows
    the LITERAL prefix as a trailing ``, <prefix>`` slot. Redundancy with the
    type name is judged by a *naive human* reader (``addr1`` does not obviously
    imply Cardano), so both are always shown — no collapse.
  * Fold-prefix schemes (did/urn/gitoid/swhid) already render their prefix as
    PRIMARY and get NO extra slot (it would double).
  * The prefix is the only ELASTIC element: truncated to the character budget
    the grid leaves on the label line (fixed 0.6 em advance constant), with a
    floor that keeps a few leading chars + ``...`` so a long prefix (only SSH's
    structural header) never collapses to a bare ``...``.
  * The large-input marker is ``+hash `` (bold dark-red), renamed from
    ``fingerprint of ``.
  * SSH ECDSA curves render ``ecdsa-p256`` in the label; ``data-qualifiers``
    keeps the faithful ``ecdsa-nistp256``.
"""
from lxml import etree
import pytest

from entviz.characterize import (
    characterize,
    render_label,
    _fit_prefix,
    _stripped_prefix,
    TRUNC_MARKER,
)
from entviz.pipeline import render


def _top(entropy: str) -> str:
    """The rendered top-strip label (document order, all tspans joined)."""
    root = etree.fromstring(render(entropy).encode())
    g = root.xpath('//*[local-name()="g" and @data-channel="label-top"]')
    assert g, "missing label-top group"
    return "".join(g[0].itertext())


# --- The locked per-scheme rendered labels (pipeline; prefix fits or floors) ---
_RENDERED = {
    "eth":          ("0x742d35cc6634c0532925a3b844bc454e4438f44e", "ETH, 0x"),
    "btc-legacy":   ("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "BTC, 1"),
    "xrp":          ("rEb8TK3gBgk5auZkwc6sHnwrGVJH8DuaLh", "XRP, r"),
    "btc-segwit":   ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "BTC, bc1"),
    "ltc":          ("ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n9", "LTC, ltc1"),
    "bch":          ("bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a",
                     "BCH, bitcoincash:"),
    "cosmos":       ("cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e",
                     "bech32, cosmos1"),
    "osmo":         ("osmo1qqqsyqcyq5rqwzqfpg9scrgwpugpzysntdz28t",
                     "bech32, osmo1"),
    "xlm-account":  ("GCKFBEIYTKP5RDBQMUTAPDCDHF2TR4LPNRGW4JBQQTQUYZP4LDKP3SGM",
                     "XLM, G"),
    "xlm-muxed":    ("MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVAAAAAAAAAAAAAJLK",
                     "XLM, M"),
    "cid-v0":       ("QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG", "CIDv0, Qm"),
    "cid-v1":       ("bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
                     "CIDv1, dag-pb, b"),
    "cid-v1-raw":   ("bafkreigh2akiscaildcqabsyg3dfr6chu3fgpregiymsck7e7aqa4s52zy",
                     "CIDv1, raw, b"),
    # Cardano Shelley is >512-bit -> the +hash marker; addr1 fits.
    "ada-shelley":  ("addr1qyqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xmyv4nxw6rf"
                     "df4kcmtwdac8zunnw36hvamc09a8klra0elsr0jfpr", "+hash ADA, addr1"),
    # No stripped front prefix -> no trailing slot (unchanged from v14).
    "uuid":         ("550e8400-e29b-41d4-a716-446655440000", "UUID"),
    "lei":          ("5493001KJTIIGC8Y1R12", "LEI"),
    "hex":          ("a1b2c3d4e5f6a7b8", "hex, 64-bit"),
    # Fold-prefix schemes: prefix is PRIMARY, no doubling.
    "did-key":      ("did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
                     "did:key"),
    "urn-isbn":     ("urn:isbn:0451450523", "urn:isbn"),
    "gitoid":       ("gitoid:blob:sha256:473a0f4c3be8a93681a267e3b1e9a7dcda118543"
                     "6fe141f7749120a303721813", "gitoid:blob:sha256"),
    "swhid":        ("swh:1:rev:309cf2674ee7a0749978cf8265ab91a60aea0f7d",
                     "swh:1:rev"),
    # Large bare inputs: +hash marker, no prefix.
    "hex-1024":     ("0123456789abcdef" * 16, "+hash hex, 1024-bit"),
}


@pytest.mark.parametrize("vid", sorted(_RENDERED))
def test_rendered_top_label(vid):
    entropy, expected = _RENDERED[vid]
    assert _top(entropy) == expected, f"{vid}: got {_top(entropy)!r}, want {expected!r}"


def test_fold_prefix_schemes_do_not_double_the_prefix():
    # A did:/urn:/gitoid:/swhid: prefix shows once (as PRIMARY), never twice.
    for vid in ("did-key", "urn-isbn", "gitoid", "swhid"):
        entropy, _ = _RENDERED[vid]
        top = _top(entropy)
        assert top.count(top.split(":")[0]) == 1 or "," not in top, top
        assert _stripped_prefix(characterize(entropy)) is None, vid


# --- SSH: the structural header is a long prefix -> truncates against the line ---

_SSH_ED25519 = ("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDtJVH9hM+2DyhmgRZBfeIDoVqC"
                "TbXY+0nKlS5pTkkXY user@example.com")
_SSH_ECDSA = ("ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNT"
              "YAAABBBNSBA0Md9M/Cwp0J32Rvk/aiElw77t6l9YQbMmJSP4PfybRxeGP4fqsrIvr6"
              "ckdRms5N8Bp/kvug/iAgX6OK59E=")


def test_ssh_prefix_truncates_but_keeps_head_and_ellipsis():
    # The pipeline budget leaves the SSH header almost no room, so it shows a few
    # leading chars + '...', NEVER a bare '...' (the floor) and never in full.
    top = _top(_SSH_ED25519)
    assert top.startswith("SSH, ed25519, 264-bit, ")
    prefix_slot = top.rsplit(", ", 1)[1]
    assert prefix_slot.endswith("...")
    assert prefix_slot != "..."           # floor kept ≥ _PREFIX_MIN_HEAD chars
    assert prefix_slot.startswith("AAAA")


def test_ssh_pure_projection_shows_full_prefix_without_budget():
    # render_label with no line_chars does not truncate: the full header appears.
    ch = characterize(_SSH_ED25519)
    top, _ = render_label(ch)
    assert top == "SSH, ed25519, 264-bit, AAAAC3NzaC1lZDI1NTE5AAAA"


def test_ssh_ecdsa_curve_is_p256_in_label_but_faithful_in_qualifiers():
    # Label projection strips 'nist'; the characterization qualifier is faithful.
    ch = characterize(_SSH_ECDSA)
    assert ch["qualifiers"]["algorithm"] == "ecdsa-nistp256"
    top = _top(_SSH_ECDSA)
    assert "ecdsa-p256" in top
    assert "nistp256" not in top


# --- The +hash marker (renamed from 'fingerprint of') ---


def test_plus_hash_marker_constant():
    assert TRUNC_MARKER == "+hash "


def test_plus_hash_marker_is_bold_dark_red():
    svg = etree.fromstring(render("ab" * 100).encode())  # 800-bit -> truncated
    marker = None
    for el in svg.xpath('//*[local-name()="text" or local-name()="tspan"]'):
        if el.text and el.text.startswith("+hash"):
            marker = el
            break
    assert marker is not None, "no +hash marker rendered"
    fill = (marker.get("fill") or "") + (marker.get("style") or "")
    assert "#a00000" in fill.lower()
    weight = (marker.get("font-weight") or "") + (marker.get("style") or "")
    assert "bold" in weight.lower()


# --- _fit_prefix unit behavior (the truncate-to-fit rule) ---


@pytest.mark.parametrize("prefix,avail,expected", [
    ("0x", 20, "0x"),                       # fits -> verbatim
    ("bitcoincash:", 12, "bitcoincash:"),   # exactly fits
    ("bitcoincash:", 8, "bitco..."),        # 8 - 3 = 5 head chars + '...'
    ("AAAAC3NzaC1lZDI1NTE5AAAA", 1, "AAAA..."),   # floored to _PREFIX_MIN_HEAD
    ("AAAAC3NzaC1lZDI1NTE5AAAA", -5, "AAAA..."),  # negative budget -> floor
])
def test_fit_prefix(prefix, avail, expected):
    assert _fit_prefix(prefix, avail) == expected
