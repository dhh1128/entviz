"""
Multicodec-driven labelling for IPFS CIDs.

A CIDv1 is self-describing: after the multibase selector its bytes are
`<version-varint><content-codec-varint><multihash>`, and the multihash is
`<hash-fn-varint><length-varint><digest>`. Those leading varints are real
bytes physically present in the input, so decoding them to name the
content codec and hash function is deterministic and sound (unlike a
content-sniffing guess). It is also LABEL-ONLY: the core stays the full
base32 body and the fingerprint is unchanged — only the type label gets
richer. See `this.i:mult1c0d`.

CIDv0 (`Qm…`) is dag-pb + sha2-256 by definition.
"""
import base64

from entviz.entropy import (
    parse, parse_ipfs_cid, decode_multicodec, _b32_nopad_decode,
    MULTICODEC_CONTENT, HEX,
)
from entviz.fingerprint import compute_fingerprint


# bafybei… → version 1, dag-pb (0x70), sha2-256 (0x12)
CID_DAGPB = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
# bafkrei… → version 1, raw (0x55), sha2-256 (0x12)
CID_RAW = "bafkreigh2akiscaildcqabsyg3dfr6chu3fgpregiymsck7e7aqa4s52zy"
CID_V0 = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"


def test_multicodec_table_has_common_codecs():
    assert MULTICODEC_CONTENT[0x55] == "raw"
    assert MULTICODEC_CONTENT[0x70] == "dag-pb"
    assert MULTICODEC_CONTENT[0x71] == "dag-cbor"


def test_cidv1_codec_shown_hash_elided_when_default():
    # The codec always shows; the near-universal sha2-256 hash is elided
    # (silent default, loud departure). See this.i:lbldedup.
    assert parse_ipfs_cid(CID_DAGPB).type == "CIDv1 dag-pb"
    assert parse_ipfs_cid(CID_RAW).type == "CIDv1 raw"


def test_cidv1_non_default_hash_is_shown():
    # A CIDv1 whose hash is NOT sha2-256 surfaces the hash as a departure.
    # Build one directly: version 1, dag-pb (0x70), sha3-256 (0x15), len 32.
    body = bytes([0x01, 0x70, 0x15, 0x20]) + bytes(range(32))
    cid = "b" + base64.b32encode(body).decode().lower().rstrip("=")
    assert parse_ipfs_cid(cid).type == "CIDv1 dag-pb/sha3-256"


def test_cidv0_label_is_bare():
    # v0 is dag-pb/sha2-256 by definition — both are the default, so elided.
    assert parse_ipfs_cid(CID_V0).type == "CIDv0"


def test_enrichment_is_label_only_core_and_fingerprint_unchanged():
    # The decoded label must NOT change what entropy is visualized: the
    # core is still the full base32 body, so the fingerprint is identical
    # to what the un-enriched parser produced.
    p = parse_ipfs_cid(CID_DAGPB)
    assert p.core == CID_DAGPB[1:].upper()        # 'b' stripped, base32 upper
    assert compute_fingerprint(p.core) == compute_fingerprint(CID_DAGPB[1:].upper())


def test_undecodable_cidv1_falls_back_to_generic_label():
    # A structurally valid 'b…' base32 string whose interior is not a
    # sensible version/codec/hash must still parse, just with the plain
    # label rather than crashing or mislabelling.
    assert decode_multicodec(b"\xff\xff\xff") is None


def test_decode_multicodec_returns_codec_hash_pair():
    described = decode_multicodec(_b32_nopad_decode(CID_DAGPB[1:]))
    assert described == ("dag-pb", "sha2-256")


def test_dispatches_through_parse():
    assert parse(CID_DAGPB).type == "CIDv1 dag-pb"
    assert parse(CID_V0).type == "CIDv0"
