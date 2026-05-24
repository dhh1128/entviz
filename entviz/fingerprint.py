"""
Fingerprint computation and tokenization.

The fingerprint is the SHA-512 hash of the normalized entropy. It exists
because input entropy may be chosen rather than generated (UUIDs, raw hex,
base64url blobs), in which case the input itself has no avalanche effect:
two inputs that differ by a single bit look almost identical. Hashing first
guarantees that any input difference explodes across every fingerprint-
driven channel of the entviz.

The 64-byte digest is encoded as base64url (no padding) and tokenized by
the same routine that tokenizes entropy. This always yields exactly 22
ftoks: 21 full ftoks of 4 base64 characters each, plus one partial ftok
formed from the trailing byte (encoded as 2 base64 chars) and extended
to 24 bits by the standard partial-token bit-extension rule.

Ftoks are typed distinctly from Tokens so the type system distinguishes
which data source a value came from. Token quants drive text and nucleus
background color; ftok quants drive everything else.
"""
import base64
import hashlib
from collections import namedtuple

from .entropy import tokenize, get_median_token, get_quartile_tokens

Ftok = namedtuple('Ftok', ['text', 'index', 'quant'])

_DIGEST_LEN = 64
_EXPECTED_FTOK_COUNT = 22


def compute_fingerprint(normalized_core: str) -> bytes:
    """Return SHA-512 of the UTF-8 bytes of the normalized entropy core."""
    return hashlib.sha512(normalized_core.encode('utf-8')).digest()


def tokenize_fingerprint(digest: bytes) -> list[Ftok]:
    """Split a 64-byte digest into exactly 22 Ftoks of 24 bits each."""
    if len(digest) != _DIGEST_LEN:
        raise ValueError(
            f"fingerprint must be {_DIGEST_LEN} bytes, got {len(digest)}"
        )
    b64 = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    tokens = tokenize(b64, 'base64')
    assert len(tokens) == _EXPECTED_FTOK_COUNT, (
        f"expected {_EXPECTED_FTOK_COUNT} ftoks, got {len(tokens)}"
    )
    return [Ftok(t.text, i, t.quant) for i, t in enumerate(tokens)]


# The median/quartile selection logic is identical to v1's token-based
# functions because Ftok and Token share the (text, index, quant) shape.
# These named aliases make ftok-mode call sites unambiguous at the
# pipeline layer; both return Ftok instances (the input type is preserved).
get_median_ftok = get_median_token
get_quartile_ftoks = get_quartile_tokens
