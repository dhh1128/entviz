"""v14: the label strips are a pure projection of the entropy characterization
(one `render_label(characterization)` grammar), and bound checksums are VERIFIED
(a structural match with a bad checksum is rejected).

See docs/spec.md → "Label strips" + "Checksum verification", this.i:v14lbl, and
reviews/v14-label-redesign.md.
"""
import pytest

from entviz.characterize import characterize, render_label
from entviz.entropy import (
    parse,
    Base58CheckError,
    Bech32ChecksumError,
    LEIChecksumError,
    EIP55ChecksumError,
)
from entviz.pipeline import render


# ---------------------------------------------------------------------------
# Task A — label grammar (a projection of the characterization)
# ---------------------------------------------------------------------------

# The locked before→after table (reviews/v14-label-redesign.md): the projected
# TOP label for each worked input. Truncated (>512-bit) inputs carry the leading
# '+hash ' marker (v15, renamed from 'fingerprint of '). These cases use the pure
# render_label() with no line_chars budget, so any prefix slot is shown in full
# (never truncated) — the grid-budget truncation is covered in
# tests/test_v15_prefix_labels.py.
_TOP_LABEL_CASES = {
    # id: (input, expected_top)
    "cesr-aid-b": ("BKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx", "CESR, Ed25519 nt"),
    "cesr-aid-d": ("DKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx", "CESR, Ed25519"),
    "cesr-said-e": ("EBfdlu8R27Fbx_ehrqwImnK_8Cm79sqbAQ4caaZG_LFv", "CESR, Blake3-256"),
    "hex-256": (
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "hex, 256-bit"),
    "text-lorem": (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "text, 56-byte"),
    "did-key-ed25519": (
        "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK", "did:key"),
    "urn-isbn": ("urn:isbn:0451450523", "urn:isbn"),
    # v15: schemes that strip a front prefix now echo it as a trailing slot
    # (the CID multibase 'b', the '0x'/'bc1'/'1' sigils). SSH (whose prefix
    # truncates against the grid budget) is tested separately in
    # tests/test_v15_prefix_labels.py — its pure-vs-rendered forms differ.
    "cid-v1": (
        "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
        "CIDv1, dag-pb, b"),
    "cid-v0": (
        "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG", "CIDv0, Qm"),
    "eth": ("0x742d35cc6634c0532925a3b844bc454e4438f44e", "ETH, 0x"),
    "btc-segwit": ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "BTC, bc1"),
    "btc-legacy": ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "BTC, 1"),
    "uuid": ("550e8400-e29b-41d4-a716-446655440000", "UUID"),
    "lei": ("5493001KJTIIGC8Y1R12", "LEI"),
    "snowflake": ("80351110224678912", "snowflake"),
    "gitoid": (
        "gitoid:blob:sha256:473a0f4c3be8a93681a267e3b1e9a7dcda1185436fe141f7749"
        "120a303721813",
        "gitoid:blob:sha256"),
    "swhid-rev": (
        "swh:1:rev:309cf2674ee7a0749978cf8265ab91a60aea0f7d", "swh:1:rev"),
    "b64-large": (
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvkLpZUVjlW8zG3p4G7m7Q1xQfP"
        "8aZ8WUEpiE8WxC8mTLg3aN8gqK2y1zGfKbXc9p2YtNvJ5h0sX",
        "+hash b64, 712-bit"),
}


def _is_truncated(entropy: str) -> bool:
    from entviz.entropy import parse as _p, tokenize_entropy, BASE64URL
    import base64
    p = _p(entropy.strip())
    if p is None:
        core = base64.urlsafe_b64encode(entropy.strip().encode()).decode().rstrip("=")
        alpha = BASE64URL
    else:
        core, alpha = p.core, p.alphabet
    _, tr = tokenize_entropy(core, alpha)
    return tr


@pytest.mark.parametrize("vid", sorted(_TOP_LABEL_CASES))
def test_render_label_projection_matches_locked_table(vid):
    entropy, expected = _TOP_LABEL_CASES[vid]
    ch = characterize(entropy)
    top, _bottom = render_label(ch, truncated=_is_truncated(entropy))
    assert top == expected, f"{vid}: got {top!r}, want {expected!r}"


@pytest.mark.parametrize("vid", sorted(_TOP_LABEL_CASES))
def test_pipeline_renders_projected_top_label(vid):
    """The rendered SVG's label-top strip carries the projected label (proving
    the pipeline wires render_label, not the old per-parser fusing)."""
    from lxml import etree
    entropy, expected = _TOP_LABEL_CASES[vid]
    root = etree.fromstring(render(entropy).encode())
    top_g = root.xpath('//*[local-name()="g" and @data-channel="label-top"]')
    assert top_g, f"{vid}: missing label-top group"
    joined = "".join(top_g[0].itertext())
    assert joined == expected, f"{vid}: rendered {joined!r}, want {expected!r}"


def test_top_label_has_no_trailing_colon():
    # The v14 grammar dropped the trailing ':'. (v15: a truncated PREFIX slot may
    # legitimately end in '...' as an elision marker, so the no-trailing-'...'
    # rule no longer holds in general; these untruncated cases still never do.)
    for entropy, _expected in _TOP_LABEL_CASES.values():
        ch = characterize(entropy)
        top, _ = render_label(ch, truncated=_is_truncated(entropy))
        assert not top.endswith(":"), top


def test_bottom_label_is_bound_checksum_then_note():
    # A base58check suffix shows as the bottom strip; a note follows in parens.
    ch = characterize("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    _top, bottom = render_label(ch, suffix="vfNa", note="btc")
    assert bottom == "...vfNa (btc)"
    _top, bottom = render_label(ch, suffix="vfNa")
    assert bottom == "...vfNa"
    _top, bottom = render_label(characterize("a1b2c3d4e5f6a7b8"), note="hi")
    assert bottom == "(hi)"


def test_ssh_size_is_faithful_field_projection():
    # The label SIZE slot is the characterization's size_bits verbatim (264 for
    # this ed25519 key), NOT a re-derived 256 semantic key size.
    entropy = ("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDtJVH9hM+2DyhmgRZBfeIDoVqC"
               "TbXY+0nKlS5pTkkXY user@example.com")
    ch = characterize(entropy)
    assert ch["size_bits"] == 264
    top, _ = render_label(ch)
    # v15: with no line_chars budget the stripped SSH header is appended in full;
    # the SIZE slot is still the faithful 264, not a re-derived 256.
    assert top.startswith("SSH, ed25519, 264-bit, ")


# ---------------------------------------------------------------------------
# Task B — checksum verification (reject on invalid)
# ---------------------------------------------------------------------------

# Each is a valid render vector with ONE checksum char/case corrupted.
_BAD_CHECKSUM_CASES = {
    "btc-legacy": ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb", Base58CheckError),
    "btc-segwit": ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5", Bech32ChecksumError),
    "ltc-bech32": ("ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n8", Bech32ChecksumError),
    "cosmos": ("cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363f", Bech32ChecksumError),
    # BCH CashAddr uses a 40-bit BCH checksum, not the bech32 polymod; a
    # one-char-corrupted (a->q) corpus address must reject. Shares the
    # Bech32ChecksumError class ("Bitcoin Cash" kind).
    "bch-cashaddr": (
        "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6q",
        Bech32ChecksumError,
    ),
    "lei": ("5493001KJTIIGC8Y1R13", LEIChecksumError),
    "eip55": ("0x5aaeb6053F3E94C9b9A09f33669435E7Ef1BeAed", EIP55ChecksumError),
}


@pytest.mark.parametrize("vid", sorted(_BAD_CHECKSUM_CASES))
def test_bad_checksum_is_rejected(vid):
    entropy, exc = _BAD_CHECKSUM_CASES[vid]
    with pytest.raises(exc):
        render(entropy)
    # All the new checksum errors subclass ValueError (like EIP55ChecksumError),
    # so existing ValueError handlers keep working.
    with pytest.raises(ValueError):
        parse(entropy)


# Each valid counterpart MUST still render (guards against over-eager rejection).
_VALID_CHECKSUM_CASES = [
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",             # BTC legacy (Satoshi genesis)
    "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",     # BTC segwit (BIP-173)
    "ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n9",    # LTC bech32
    "cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e",  # cosmos generic bech32
    "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a",  # BCH CashAddr (valid)
    "qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a",     # BCH CashAddr, bare (bitcoincash HRP)
    "5493001KJTIIGC8Y1R12",                            # LEI (Bloomberg)
    "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",     # EIP-55 (valid mixed case)
]


@pytest.mark.parametrize("entropy", _VALID_CHECKSUM_CASES)
def test_valid_checksum_still_renders(entropy):
    svg = render(entropy)
    assert svg.startswith("<svg") or svg.lstrip().startswith("<svg")


# ---------------------------------------------------------------------------
# Task B (cont.) — Cardano Byron surfaces NO checksum suffix
# ---------------------------------------------------------------------------

# Byron's integrity check is a CRC-32 inside the CBOR-decoded payload, not a
# trailing base58 checksum field. v14 stops peeling the last 6 base58 chars off
# as a false "suffix": the whole body is the core, suffix is None, and Byron
# still renders (it is recognized, just not checksum-verified/shown). Shelley
# (bech32) IS verified and keeps its suffix.
@pytest.mark.parametrize("entropy", [
    "Ae2tdPwUPEZ7SZaSCeU8sGZXGZ7YrVc96FnzYdZcLkbry4CqUKax9dNeEoe",   # Byron short
    "DdzFFzCqrht1D2Tv5F9HLtZHEd4P9Tddf9DFv3d4KXa2RxudcL4uHKWtc2HfiDopch5UHyZkXQx7",  # Byron long
])
def test_cardano_byron_has_no_checksum_suffix(entropy):
    p = parse(entropy)
    assert p is not None
    assert p.type == "ADA Byron"
    assert p.suffix is None                      # no false checksum surfaced
    assert p.prefix + p.core == entropy          # whole body preserved in core
    svg = render(entropy)                         # still renders
    assert svg.lstrip().startswith("<svg")
