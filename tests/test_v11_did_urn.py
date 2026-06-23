"""v11 DID + URN handling (docs/spec.md *Decentralized Identifiers* and
*Uniform Resource Names*; this.i:d1dm3th0).

DIDs and URNs share one generic path: the scheme+namespace (`did:<method>:` /
`urn:<nid>:`) is identity and binds the fingerprint by PREFIX-FOLD
(prefix_semantic=True, so the pipeline hashes `prefix ‖ core`); the body
(method-specific-id / NSS) is the core, kept VERBATIM and tokenized as
base64url; the trailing resolution components (DID URL `/?#`, URN r-/q-/f
`?+`/`?=`/`#`) are a FREE annotation and are DROPPED (never a suffix); and the
label has no type (the `did:<method>:...` / `urn:<nid>:...` self-describing
prefix, as for SWHID/gitoid).

Two differences: a DID body ends at the first `/`, `?`, or `#`; a URN NSS keeps
`/` and ends only at `?` or `#`. A DID preserves all case; a URN lowercases its
`urn:<nid>:` prefix (RFC 8141 — NID case-insensitive) but preserves NSS case.
"""

from entviz.entropy import parse, parse_did, parse_urn, BASE64URL
from entviz.fingerprint import compute_fingerprint


# --- helpers ---------------------------------------------------------------

def _fold(parsed):
    """Reproduce the pipeline's prefix-fold hash input for a Parsed result."""
    if parsed.prefix and parsed.prefix_semantic:
        return parsed.prefix + parsed.core
    return parsed.core


# === DID ===================================================================

def test_did_basic_web():
    p = parse_did("did:web:example.com")
    assert p is not None
    assert p.type == ""                      # no-type label (did:web:...)
    assert p.alphabet == BASE64URL
    assert p.prefix == "did:web:"
    assert p.core == "example.com"
    assert p.suffix is None
    assert p.prefix_semantic is True         # method binds via prefix-fold


def test_did_multisegment_colon_path_kept_in_core():
    # Colons inside the method-specific-id are body, not a terminator.
    p = parse_did("did:web:example.com:user:alice")
    assert p.prefix == "did:web:"
    assert p.core == "example.com:user:alice"


def test_did_percent_encoded_port_kept():
    p = parse_did("did:web:example.com%3A3000:user:alice")
    assert p.core == "example.com%3A3000:user:alice"


def test_did_url_path_dropped():
    p = parse_did("did:web:example.com/path/path")
    assert p.core == "example.com"           # path is a free annotation
    assert p.suffix is None


def test_did_url_query_dropped():
    p = parse_did("did:webs:abc123swoeireulf?arg=val")
    assert p.core == "abc123swoeireulf"
    assert p.suffix is None


def test_did_url_fragment_dropped():
    # Fragments previously broke parsing entirely (fell to UTF-8 fallback).
    p = parse_did("did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK#key-1")
    assert p.prefix == "did:key:"
    assert p.core == "z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"
    assert p.suffix is None


def test_did_webvh_scid_and_domain_both_kept():
    p = parse_did("did:webvh:QmQyDxVnosYTzHAMbzYDRZkVrD32ea9Sr2XNs8NkgMB5mn:domain.example")
    assert p.prefix == "did:webvh:"
    assert p.core == "QmQyDxVnosYTzHAMbzYDRZkVrD32ea9Sr2XNs8NkgMB5mn:domain.example"


def test_did_method_binds_fingerprint():
    # The bug v11 fixes: method must bind, so same body + different method
    # must NOT collide. (prefix-fold => hash over `prefix ‖ core`.)
    web = parse_did("did:web:sharedbody")
    key = parse_did("did:key:sharedbody")
    assert web.core == key.core == "sharedbody"
    assert web.prefix != key.prefix
    assert _fold(web) != _fold(key)
    assert compute_fingerprint(_fold(web)) != compute_fingerprint(_fold(key))


def test_did_case_preserved():
    # DIDs are case-sensitive (DID Core); the body is NOT case-folded.
    upper = parse_did("did:key:z6MkABCDEF")
    lower = parse_did("did:key:z6mkabcdef")
    assert upper.core == "z6MkABCDEF"
    assert lower.core == "z6mkabcdef"
    assert compute_fingerprint(_fold(upper)) != compute_fingerprint(_fold(lower))


def test_did_real_examples_recognized():
    # A spread of real, sourced DIDs across encodings — all ride one path.
    samples = {
        "did:key:zQ3shokFTS3brHcDQrn82RUDfCZESWL1ZdCEJwekUDPQiYBme": "did:key:",
        "did:peer:2.Ez6LSt4Jscr227NFyuzKHT85haVE4AFVXm1tDwYeZ5xenxMmW.Vz6MkfvwnoNS6Cto38MEMbqdnypVDN7gS4oAMaHFkjAUse5JE": "did:peer:",
        "did:ion:EiClkZMDxPKqC9c-umQfTkR8vvZ9JPhl_xLDI9Nfk38w5w": "did:ion:",
        "did:ethr:0x5:0xf3beac30c498d9e26865f34fcaa57dbb935b0d74": "did:ethr:",
        "did:pkh:eip155:1:0xb9c5714089478a327f09197987f16f9e5d936e8a": "did:pkh:",
    }
    for did, prefix in samples.items():
        p = parse_did(did)
        assert p is not None, did
        assert p.prefix == prefix
        assert p.prefix_semantic is True
        assert p.type == ""
        assert p.core == did[len(prefix):]   # whole body verbatim, no URL here


def test_did_peer_dotted_body_lossless():
    # did:peer rides the generic base58/base64url path; the `.` separators and
    # V/E purpose codes stay verbatim in the core (identity-lossless).
    did = "did:peer:2.Ez6LSt4Jscr227NFyuzKHT85haVE4AFVXm1tDwYeZ5xenxMmW.Vz6MkfvwnoNS6Cto38MEMbqdnypVDN7gS4oAMaHFkjAUse5JE"
    p = parse_did(did)
    assert "." in p.core and ".V" in p.core and ".E" in p.core


def test_did_malformed_falls_through():
    assert parse_did("did:") is None
    assert parse_did("did::nomethod") is None
    assert parse_did("did:web:") is None          # empty method-specific-id
    assert parse_did("notadid") is None


def test_did_dispatch_via_parse():
    p = parse("did:web:example.com:user:alice")
    assert p.prefix == "did:web:"
    assert p.core == "example.com:user:alice"


# === URN ===================================================================

def test_urn_basic_isbn():
    p = parse_urn("urn:isbn:0451450523")
    assert p is not None
    assert p.type == ""
    assert p.alphabet == BASE64URL
    assert p.prefix == "urn:isbn:"
    assert p.core == "0451450523"
    assert p.suffix is None
    assert p.prefix_semantic is True


def test_urn_nid_lowercased_nss_preserved():
    # RFC 8141: scheme + NID case-insensitive (lowercase the prefix); NSS
    # case-sensitive (preserve it).
    p = parse_urn("URN:ISBN:0451450523")
    assert p.prefix == "urn:isbn:"
    assert p.core == "0451450523"
    mixed = parse_urn("urn:example:AbCdEf")
    assert mixed.prefix == "urn:example:"
    assert mixed.core == "AbCdEf"             # NSS case untouched


def test_urn_nss_keeps_slash():
    # `/` is a legal NSS character and part of identity (unlike a DID path).
    p = parse_urn("urn:example:a123,z456/foo")
    assert p.core == "a123,z456/foo"


def test_urn_nss_keeps_colons():
    assert parse_urn("urn:oid:2.16.840.1.113883.6.1").core == "2.16.840.1.113883.6.1"
    assert parse_urn("urn:lex:eu:council:directive").core == "eu:council:directive"


def test_urn_components_dropped():
    # q-component (?=) + f-component (#) — RFC 8141 says not part of equivalence.
    p = parse_urn("urn:example:weather?=op=map&lat=39#frag")
    assert p.core == "weather"
    assert p.suffix is None
    # r-component (?+)
    assert parse_urn("urn:example:foo?+CCResolve:cc=uk").core == "foo"
    # bare fragment
    assert parse_urn("urn:example:foo#bar").core == "foo"


def test_urn_uuid_generic_not_special_cased():
    # urn:uuid rides the generic path — NSS kept verbatim, NOT re-parsed as a
    # bare UUID (no dash-stripping).
    p = parse_urn("urn:uuid:f81d4fae-7dec-11d0-a765-00a0c91e6bf6")
    assert p.prefix == "urn:uuid:"
    assert p.core == "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"


def test_urn_nid_binds_fingerprint():
    isbn = parse_urn("urn:isbn:0451450523")
    issn = parse_urn("urn:issn:0451450523")
    assert isbn.core == issn.core
    assert compute_fingerprint(_fold(isbn)) != compute_fingerprint(_fold(issn))


def test_urn_malformed_falls_through():
    assert parse_urn("urn:isbn") is None      # no NSS
    assert parse_urn("urn:") is None
    assert parse_urn("noturn:isbn:x") is None


def test_urn_dispatch_via_parse():
    p = parse("URN:ISBN:0451450523")
    assert p.prefix == "urn:isbn:"
    assert p.core == "0451450523"
