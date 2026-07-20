"""Entropy characterization model.

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

# Closed role enum. Nothing outside this set may appear.
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

# CESR primitives that are recognized but carry NO role in the closed enum
# {key, signature, digest, address, identifier}. A Dater ("datetime") is a
# low-entropy, directly human-readable temporal value — entviz recognizes it
# only to LABEL it correctly (not `raw`), NOT to endorse visualizing it as
# entropy. It MUST short-circuit to role=None here rather than fall through to
# the ROLE_KEY default below. See docs/spec.md role principle and
# this.i:idxs1gs0. (Checked before the sig/digest markers so a future temporal
# primitive whose name happened to contain one of those substrings stays
# role-less.)
_CESR_NONENTROPY_MARKERS = ("datetime",)


def _cesr_role(name: str):
    low = name.lower()
    if any(m.lower() in low for m in _CESR_NONENTROPY_MARKERS):
        return None
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


# ---------------------------------------------------------------------------
# Label projection.
#
# The visible top/bottom label strips are a PURE PROJECTION of the eight
# characterization fields through one grammar — no per-parser string fusing.
# Every implementation renders the same strips by running this same function
# over the shared fields. See docs/spec.md -> "Label strips" and
# reviews/v14-label-redesign.md.
#
#   top    = [fingerprint of ]PRIMARY[, MOD]...[, SIZE]
#   bottom = ...<suffix>[ (<note>)]
#
# Slot separator is ", " (comma-space); no trailing ':' or '...'.
# ---------------------------------------------------------------------------

# Bare-encoding display shortenings for the PRIMARY slot when scheme is null
# and the basis is decoded (the encoding name IS the primary). Mirrors the
# pre-v14 pipeline renaming base64->b64, base64url->b64url; the other alphabet
# names (hex, base32, base58, bech32, crockford32, decimal) show verbatim.
_ENCODING_PRIMARY = {
    "base64": "b64",
    "base64url": "b64url",
}

# scheme -> visible PRIMARY short-name for the non-self-describing schemes.
# The characterization `scheme` field is lowercase (btc/eth/...); the label
# uses the conventional display casing (BTC/ETH/UUID/...). CID is special-cased
# (CIDv0 / CIDv1 from qualifiers.version); the self-describing prefix schemes
# (did/urn/gitoid/swhid) reconstruct their prefix from qualifiers and never
# reach this map.
_SCHEME_PRIMARY = {
    "eth": "ETH",
    "btc": "BTC",
    "ltc": "LTC",
    "bch": "BCH",
    "ada": "ADA",
    "xrp": "XRP",
    "stellar": "XLM",
    "eos": "EOS",
    "uuid": "UUID",
    "ulid": "ULID",
    "lei": "LEI",
    "snowflake": "snowflake",
    "ssh": "SSH",
    "cesr": "CESR",
    "bech32": "bech32",
    "multihash": "multihash",
}

# Blockchain schemes whose network qualifier, when it departs from mainnet,
# surfaces as a MOD (testnet loud; mainnet silent). The legacy/segwit `variant`
# is DROPPED entirely (v14).
_BLOCKCHAIN_SCHEMES = frozenset(
    {"btc", "ltc", "bch", "ada", "eth", "xrp", "stellar", "eos", "bech32"})


def _primary(ch: dict) -> str:
    """The PRIMARY slot: the always-present head of the top label."""
    scheme = ch["scheme"]
    q = ch["qualifiers"]
    if scheme is None:
        # Bare encoding or UTF-8 fallback.
        if ch["size_basis"] == "utf8":
            return "text"
        enc = ch["encoding"]
        return _ENCODING_PRIMARY.get(enc, enc)
    if scheme == "did":
        return f"did:{q['method']}"
    if scheme == "urn":
        return f"urn:{q['nid']}"
    if scheme == "gitoid":
        # gitoid:<object>:<algorithm> (e.g. gitoid:blob:sha256).
        return f"gitoid:{q.get('object', '')}:{q.get('algorithm', '')}"
    if scheme == "swhid":
        # swh:1:<object> (e.g. swh:1:rev).
        return f"swh:1:{q.get('object', '')}"
    if scheme == "cid":
        return "CIDv0" if q.get("version") == 0 else "CIDv1"
    return _SCHEME_PRIMARY.get(scheme, scheme)


def _mods(ch: dict) -> list[str]:
    """The MOD slots (zero or more): silent-default / loud-departure facets."""
    scheme = ch["scheme"]
    q = ch["qualifiers"]
    mods: list[str] = []
    if scheme == "cesr":
        # The primitive with the redundant role word dropped: strip trailing
        # " pubkey" (role=key/digest is implied by the primitive).
        algo = q.get("algorithm", "")
        if algo.endswith(" pubkey"):
            algo = algo[: -len(" pubkey")]
        if algo:
            mods.append(algo)
    elif scheme == "ssh":
        algo = q.get("algorithm")
        if algo:
            # v15: shorten the ECDSA curve to its common short name for the
            # label — "ecdsa-nistp256" -> "ecdsa-p256" (there is no rival
            # non-NIST "p256"; the algorithm word stays, only the redundant
            # standards-body prefix drops). The data-qualifiers `algorithm`
            # field keeps the faithful SSH curve id ("ecdsa-nistp256").
            mods.append(algo.replace("nistp", "p"))
    elif scheme == "cid":
        # CIDv0 is dag-pb/sha2-256 by definition -> no MOD. CIDv1: codec always,
        # hash only on departure from sha2-256.
        if q.get("version") != 0:
            codec = q.get("codec")
            if codec:
                mods.append(codec)
            hash_name = q.get("hash")
            if hash_name and hash_name != "sha2-256":
                mods.append(hash_name)
    elif scheme == "multihash":
        hash_name = q.get("hash")
        if hash_name and hash_name != "sha2-256":
            mods.append(hash_name)
    elif scheme in _BLOCKCHAIN_SCHEMES:
        # Network only on departure (testnet); mainnet silent. Variant dropped.
        network = q.get("network")
        if network and network != "mainnet":
            mods.append(network)
    return mods


def _size(ch: dict):
    """The SIZE slot (zero or one), or None when omitted."""
    scheme = ch["scheme"]
    size_bits = ch["size_bits"]
    if scheme is None:
        if ch["size_basis"] == "utf8":
            return f"{size_bits // 8}-byte"
        return f"{size_bits}-bit"
    if scheme in ("ssh", "multihash"):
        return f"{size_bits}-bit"
    return None


# v15: large-input truncation marker. Prepended (bold dark-red, by the renderer)
# to the top label when the text channel is a head/fingerprint-middle/tail
# readout rather than a linear scan. Reads as "the value, augmented with a hash
# of the parts that didn't fit" — the leading "+" is additive, not substitutive,
# so it does not imply the whole picture is a digest. Replaces v14's
# "fingerprint of ". Kept in sync with entviz.pipeline (which splits on it to
# style the marker tspan). See docs/spec.md and this.i:v15pfxlbl.
TRUNC_MARKER = "+hash "

# ASCII elision marker for a truncated prefix slot (matches the bottom strip's
# "...<suffix>" convention; no Unicode ellipsis, so the printable-ASCII / unicode
# guard is satisfied and cross-implementation font behavior is uniform).
_PREFIX_ELLIPSIS = "..."

# Minimum number of LEADING prefix characters kept when the prefix is truncated.
# The label-line budget can leave a big prefix (only SSH's ~24-52 char structural
# header is ever this long) almost no room; without a floor it would collapse to
# a bare "..." that shows nothing. Keeping a few head chars honors "show the first
# few characters, then an ellipsis" — it tells the reader a long prefix was
# elided rather than merely that *something* was. 4 is enough to read "there is a
# real prefix here" without materially widening the strip.
_PREFIX_MIN_HEAD = 4


def _stripped_prefix(ch: dict):
    """The literal front prefix that was stripped from the visualized core, or
    ``None``.

    This is a leading ``bind="none"`` part — a presentation sigil peeled off the
    front (``0x``, ``bc1``, ``cosmos1``, Stellar ``G``, the SSH structural
    header, …). A folded identity prefix (``bind="fold"``: did/urn/gitoid/swhid)
    is NOT returned — it is already shown verbatim as the PRIMARY slot, so
    echoing it again would double it. A ``bind="core"`` leading part (e.g. a
    CESR derivation code, which is in the first cell) is likewise not a stripped
    prefix.
    """
    parts = ch.get("parts") or []
    if parts and parts[0].get("bind") == "none":
        return parts[0]["text"]
    return None


def _fit_prefix(prefix: str, avail: int) -> str:
    """Truncate the literal prefix slot to ``avail`` characters with a trailing
    ``...`` elision marker.

    The prefix is the sole ELASTIC label element: PRIMARY/MOD/SIZE are
    never truncated. ``avail`` is the character budget the grid leaves on the
    label line after those slots. When the prefix does not fit, it is cut to
    ``<head> + "..."``; the head length is floored at ``_PREFIX_MIN_HEAD`` so a
    long prefix on a tight line (only SSH's structural header hits this) still
    shows a few leading characters rather than collapsing to a bare ``...`` —
    honoring "show the first few characters, then an ellipsis". A prefix that
    fits is shown verbatim. The elision marker tells the reader the cells do NOT
    begin at the character right after the visible prefix.
    """
    if len(prefix) <= avail:
        return prefix
    keep = max(avail - len(_PREFIX_ELLIPSIS), _PREFIX_MIN_HEAD)
    return prefix[:keep] + _PREFIX_ELLIPSIS


def render_label(ch: dict, truncated: bool = False, suffix: str = None,
                 note: str = None, line_chars: int = None) -> tuple[str, str]:
    """Project a characterization into the (top, bottom) label strips.

    Pure function of the eight characterization fields plus the presentation
    facts the fields don't carry: whether the input was >512-bit ``truncated``,
    the bound ``suffix`` checksum, the out-of-band user ``note``, and the
    monospace ``line_chars`` budget the grid leaves for the top strip (used only
    to truncate the elastic prefix slot; ``None`` = do not truncate).

    * ``top`` = ``[+hash ]PRIMARY[, MOD]...[, SIZE][, <prefix>]`` — ", " joined,
      no trailing ``:``. The optional ``+hash `` marker is added by the
      renderer's styled bold-red tspan; it is reflected here so a text-only
      consumer still sees it. The trailing ``<prefix>`` slot (v15) echoes a
      front prefix that was stripped from the visualized core (a ``bind="none"``
      leading part) so the reader can reconcile the pasted value against the
      cells; it is the only slot that may be truncated (to ``line_chars``) and
      may then end in ``...``. Fold-prefix schemes (did/urn/gitoid/swhid) show
      their prefix as PRIMARY and get no extra slot.
    * ``bottom`` = ``...<suffix>`` then `` (<note>)`` — the bound (now-verified)
      checksum and the user caption. Empty string when neither is present. The
      bottom strip already reconciles the *end* of the value; the top prefix
      slot is its symmetric counterpart for the *front*.

    Returns plain strings; the renderer maps ``top``/``bottom`` onto the SVG
    label strips (styling the marker and note tspans). See
    ``docs/spec.md`` -> "Label strips" and ``this.i:v15pfxlbl``.
    """
    slots = [_primary(ch)]
    slots.extend(_mods(ch))
    size = _size(ch)
    if size is not None:
        slots.append(size)

    prefix = _stripped_prefix(ch)
    if prefix:
        if line_chars is not None:
            # Budget left for the prefix = the line budget minus the marker and
            # the fixed PRIMARY/MOD/SIZE core (which never truncate) and the
            # ", " that joins the prefix slot.
            marker_len = len(TRUNC_MARKER) if truncated else 0
            core_len = len(", ".join(slots))
            avail = line_chars - marker_len - core_len - len(", ")
            prefix = _fit_prefix(prefix, avail)
        slots.append(prefix)

    top = ", ".join(slots)
    if truncated:
        top = TRUNC_MARKER + top

    bottom = ""
    if suffix:
        bottom = f"...{suffix}"
    if note:
        bottom = f"{bottom} ({note})" if bottom else f"({note})"
    return top, bottom


def characterize(entropy: str) -> dict:
    """Characterize an entropy string into the structured model.

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
