"""Entropy characterization model (spec v13).

The parser (:mod:`entviz.entropy`) produces a ``Parsed`` display record whose
``type`` string fuses several orthogonal facts (scheme, semantic role,
network/variant, size). :func:`characterize` re-expresses that same recognition
along independent axes, so downstream consumers (labels, pills, dev APIs) read
structured fields instead of string-parsing the label.

The characterization is REPORTING-ONLY. It changes no rendered pixel, no
fingerprint input, and no label string. The renderer emits the eight fields
onto the root ``<svg>`` as ``data-*`` attributes (see
:func:`entviz.pipeline.render`), and the conformance model extractor recovers
them from *those attributes* — so every implementation, reference or port, is
compared against its own characterization rather than one recomputed in Python.
The attributes add no ink (the closed profile permits extra ``data-*``), so the
golden raster is unaffected. See ``docs/spec.md`` → *Entropy characterization*
and ``this.i:ch4rmod3l`` / ``this.i:s1zeb1ts``.

Axes (identical field set for every input):

* ``encoding``    — declared alphabet name (drives tokenization).
* ``scheme``      — recognizer/namespace that fired, or ``None`` for a bare
                    encoding / UTF-8 fallback.
* ``role``        — closed enum {key, signature, digest, address, identifier}
                    or ``None``; asserted ONLY from the GENERIC recognizer
                    (``this.i`` Wrinkle 3).
* ``qualifiers``  — independently-varying facets (network/variant/algorithm/
                    version/method/nid/...); ``{}`` when none.
* ``size_basis``  — ``"decoded"`` or ``"utf8"``; SCHEME-driven, never inferred
                    from alphabet or content shape.
* ``size_bits``   — value size in bits, always a multiple of 8, computed from
                    the CORE only (Resolution A). Reporting-only; NOT the
                    >512-bit truncation basis.
* ``parts``       — ordered [{text, bind}] with ``bind`` in {none, fold, core}
                    (replaces prefix + prefix_semantic).
* ``entropy_type``— derived convenience = ``scheme or encoding`` (tick 3ek3).
"""
from __future__ import annotations

from .entropy import (
    parse,
    BASE58,
    BASE36,
    DECIMAL,
)

# Closed role enum (spec v13). Nothing outside this set may appear.
ROLE_KEY = "key"
ROLE_SIGNATURE = "signature"
ROLE_DIGEST = "digest"
ROLE_ADDRESS = "address"
ROLE_IDENTIFIER = "identifier"

# Non-power-of-2 alphabets whose true density is below the token-packing
# bits_per_char convention. For these, size_bits decodes the core as a big
# integer and takes its minimal byte length (Resolution A) — it MUST NOT use
# bits_per_char (which overstates density: base58=6 vs true ~5.86, base36=6 vs
# ~5.17, decimal=4 vs ~3.32).
_INTEGER_DECODE_ALPHABETS = {"base58", "base36", "decimal"}


def _decoded_bytes_integer(core: str, alphabet) -> int:
    """Minimal byte length of ``core`` decoded as a big integer in its base.

    Used for the non-power-of-2 alphabets (base58/base36/decimal): decode the
    positional value and return ceil(bit_length / 8). Character lookup mirrors
    the tokenizer's case tolerance. An empty core (or a value of zero) is one
    byte, matching a single zero digit.
    """
    chars = alphabet.chars
    base = len(chars)
    n = 0
    for c in core:
        v = chars.find(c)
        if v < 0:
            v = chars.lower().find(c.lower())
        if v < 0:
            v = 0
        n = n * base + v
    if n == 0:
        return 1
    return (n.bit_length() + 7) // 8


def _size_bits(core: str, alphabet, size_basis: str) -> int:
    """Value size in bits from the CORE only (Resolution A).

    ``decoded`` basis: power-of-2 alphabets take
    ``floor(len(core) * bits_per_char / 8) * 8``; the non-power-of-2 alphabets
    (base58/base36/decimal) decode the integer to its minimal byte length. This
    is approximate where the core is a base58check SUBSTRING (Resolution B) —
    accepted, since size_bits feeds only the label and the coarse >512 test.

    ``utf8`` basis: the core is inherently text (DID msi, URN NSS, UTF-8
    fallback); size_bits is ``len(core UTF-8 bytes) * 8``.
    """
    if size_basis == "utf8":
        return len(core.encode("utf-8")) * 8
    if alphabet.name in _INTEGER_DECODE_ALPHABETS:
        return _decoded_bytes_integer(core, alphabet) * 8
    return ((len(core) * alphabet.bits_per_char) // 8) * 8


# ---------------------------------------------------------------------------
# scheme / role / qualifiers, keyed off the parser's display type + prefix.
#
# The parser is the single recognizer; characterize() re-expresses its result.
# `role` is asserted ONLY where the GENERIC recognizer determines it (Wrinkle
# 3): SSH decodes an algorithm -> key; CESR derivation codes -> key/digest;
# blockchains -> address; gitoid/swhid -> digest. did:/urn: fold an identity
# prefix -> identifier, NEVER the narrower per-method/namespace role (did:key is
# identifier, not key; did:pkh is identifier, not address; urn:isbn is
# identifier, not book).
# ---------------------------------------------------------------------------

# CESR derivation-code role classification, keyed off the decoded primitive
# name the parser puts in `type` ("CESR <name>"). Seeds/keys -> key; digests
# (SAID/said hashes) -> digest; signatures -> signature.
_CESR_DIGEST_MARKERS = (
    "Blake3", "Blake2b", "Blake2s", "SHA3", "SHA2", "sha",
)
_CESR_SIG_MARKERS = ("sig",)


def _cesr_role(name: str):
    low = name.lower()
    if any(m.lower() in low for m in _CESR_SIG_MARKERS):
        return ROLE_SIGNATURE
    if any(m.lower() in low for m in _CESR_DIGEST_MARKERS):
        return ROLE_DIGEST
    # seeds, public keys, ciphers, blinding factors, random numbers, tags ->
    # keying material. "pubkey", "seed", "enckey", "deckey", "cipher",
    # "blinding factor", "random ... number".
    return ROLE_KEY


def _cesr_algorithm(name: str) -> str:
    """The algorithm qualifier for a CESR primitive (the decoded code name,
    e.g. "Blake3-256", "Ed25519 pubkey"). Kept verbatim from the parser."""
    return name


def _describe_from_parsed(parsed):
    """Return (scheme, role, qualifiers, size_basis) for a Parsed record.

    ``size_basis`` is SCHEME-driven: did / urn / UTF-8-fallback are ``utf8``;
    every recognized encoding scheme is ``decoded``.
    """
    type_name = parsed.type or ""
    prefix = parsed.prefix
    q: dict = {}

    # --- Folded identity prefixes: did / urn / gitoid / swhid ---
    if prefix and parsed.prefix_semantic:
        if prefix.startswith("did:"):
            method = prefix[len("did:"):].rstrip(":")
            q["method"] = method
            # Recover an independently-varying network segment for the handful
            # of methods that carry one at the head of the msi (did:ethr:<net>:
            # <addr>). This is label-only recovery, not per-method decoding of
            # the value: role stays "identifier".
            if method == "ethr":
                head = parsed.core.split(":", 1)[0]
                q["network"] = head
            return "did", ROLE_IDENTIFIER, q, "utf8"
        if prefix.startswith("urn:"):
            nid = prefix[len("urn:"):].rstrip(":")
            q["nid"] = nid
            return "urn", ROLE_IDENTIFIER, q, "utf8"
        if prefix.startswith("gitoid:"):
            # gitoid:<object>:<algo>:
            segs = prefix.strip(":").split(":")
            if len(segs) >= 3:
                q["object"] = segs[1]
                q["algorithm"] = segs[2]
            return "gitoid", ROLE_DIGEST, q, "decoded"
        if prefix.startswith("swh:"):
            # swh:1:<type>:
            segs = prefix.strip(":").split(":")
            if len(segs) >= 3:
                q["object"] = segs[2]
            q["algorithm"] = "sha1"
            return "swhid", ROLE_DIGEST, q, "decoded"

    # --- CESR primitives: "CESR <decoded-name>" ---
    if type_name.startswith("CESR "):
        name = type_name[len("CESR "):]
        q["algorithm"] = _cesr_algorithm(name)
        return "cesr", _cesr_role(name), q, "decoded"

    # --- SSH public keys: "SSH <algorithm>" or "SSH key" ---
    if type_name.startswith("SSH"):
        rest = type_name[len("SSH"):].strip()
        if rest and rest != "key":
            q["algorithm"] = rest
        return "ssh", ROLE_KEY, q, "decoded"

    # --- Blockchain addresses ---
    if type_name.startswith("BTC"):
        q["network"] = "mainnet"
        low = type_name.lower()
        if "legacy" in low:
            q["variant"] = "legacy"
        elif "segwit" in low:
            q["variant"] = "segwit"
        return "btc", ROLE_ADDRESS, q, "decoded"
    if type_name == "BCH":
        # bitcoincash: HRP present -> mainnet; bchtest: -> testnet.
        q["network"] = "testnet" if (prefix or "").lower().startswith("bchtest") else "mainnet"
        return "bch", ROLE_ADDRESS, q, "decoded"
    if type_name.startswith("LTC"):
        q["network"] = "mainnet"
        if "legacy" in type_name.lower():
            q["variant"] = "legacy"
        return "ltc", ROLE_ADDRESS, q, "decoded"
    if type_name.startswith("ADA"):
        if "Byron" in type_name:
            q["variant"] = "byron"
        elif "Shelley" in type_name:
            q["variant"] = "shelley"
        return "ada", ROLE_ADDRESS, q, "decoded"
    if type_name == "ETH":
        return "eth", ROLE_ADDRESS, q, "decoded"
    if type_name.startswith("XLM"):
        if "muxed" in type_name:
            q["variant"] = "muxed"
        return "stellar", ROLE_ADDRESS, q, "decoded"
    if type_name == "XRP":
        return "xrp", ROLE_ADDRESS, q, "decoded"
    if type_name == "EOS":
        return "eos", ROLE_ADDRESS, q, "decoded"
    if type_name == "bech32":
        # Generic checksum-valid bech32; the HRP (before the '1') names the
        # chain, an independently-varying facet.
        if prefix and prefix.endswith("1"):
            q["hrp"] = prefix[:-1]
        return "bech32", ROLE_ADDRESS, q, "decoded"

    # --- Content identifiers (IPFS CID) ---
    if type_name.startswith("CIDv"):
        # "CIDv1 <codec>[/<hash>]" or "CIDv0".
        if type_name.startswith("CIDv0"):
            q["version"] = 0
            q["codec"] = "dag-pb"
            q["hash"] = "sha2-256"
        else:
            q["version"] = 1
            rest = type_name[len("CIDv1"):].strip()
            if rest:
                if "/" in rest:
                    codec, hash_name = rest.split("/", 1)
                    q["codec"] = codec
                    q["hash"] = hash_name
                else:
                    q["codec"] = rest
                    q["hash"] = "sha2-256"
        return "cid", ROLE_IDENTIFIER, q, "decoded"

    # --- Structured identifiers ---
    if type_name == "UUID":
        return "uuid", ROLE_IDENTIFIER, q, "decoded"
    if type_name == "ULID":
        return "ulid", ROLE_IDENTIFIER, q, "decoded"
    if type_name == "LEI":
        return "lei", ROLE_IDENTIFIER, q, "decoded"
    if type_name == "snowflake":
        return "snowflake", ROLE_IDENTIFIER, q, "decoded"
    if type_name.startswith("multihash") or "multihash" in type_name:
        return "multihash", ROLE_DIGEST, q, "decoded"

    # --- Bare encodings (hex / base64 / base64url / disproof fallbacks) ---
    # No recognizer fired beyond the alphabet; scheme is None, role unknown.
    return None, None, q, "decoded"


def _parts_from_parsed(parsed) -> list[dict]:
    """Reading-order [{text, bind}] parts (Wrinkle 4).

    * A folded identity prefix (did:/urn:/gitoid:/swh: scheme, prefix_semantic)
      -> bind="fold".
    * Any other shown prefix (presentation framing: 0x, Qm, b, G, 1, HRP,
      SSH structural bytes, bech32 <hrp>1) -> bind="none".
    * The core (incl. in-core discriminators like a CESR code) -> bind="core".
    * A shown suffix (base58check/LEI checksum) -> bind="none".
    """
    parts: list[dict] = []
    if parsed.prefix:
        bind = "fold" if parsed.prefix_semantic else "none"
        parts.append({"text": parsed.prefix, "bind": bind})
    parts.append({"text": parsed.core, "bind": "core"})
    if parsed.suffix:
        parts.append({"text": parsed.suffix, "bind": "none"})
    return parts


def characterize(entropy: str) -> dict:
    """Characterize an entropy string into the structured model (spec v13).

    Returns a plain JSON-serializable dict with keys: ``encoding``, ``scheme``,
    ``role``, ``qualifiers``, ``size_basis``, ``size_bits``, ``parts``,
    ``entropy_type``. Never raises for an in-range input: an unrecognized input
    falls back to the UTF-8 -> base64url path (scheme=None, role=None,
    size_basis="utf8", size measured over the ORIGINAL input bytes).
    """
    raw = entropy.strip()
    parsed = parse(raw)

    if parsed is None:
        # UTF-8 fallback: the value IS the text; size over the original input.
        from .entropy import BASE64URL
        import base64
        core = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
        return {
            "encoding": BASE64URL.name,
            "scheme": None,
            "role": None,
            "qualifiers": {},
            "size_basis": "utf8",
            "size_bits": len(raw.encode("utf-8")) * 8,
            "parts": [{"text": core, "bind": "core"}],
            "entropy_type": BASE64URL.name,
        }

    scheme, role, qualifiers, size_basis = _describe_from_parsed(parsed)
    size_bits = _size_bits(parsed.core, parsed.alphabet, size_basis)
    encoding = parsed.alphabet.name
    return {
        "encoding": encoding,
        "scheme": scheme,
        "role": role,
        "qualifiers": qualifiers,
        "size_basis": size_basis,
        "size_bits": size_bits,
        "parts": _parts_from_parsed(parsed),
        "entropy_type": scheme if scheme is not None else encoding,
    }
