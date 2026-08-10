"""Guards for the three things the v17 correction pass taught.

Each was found by a *port* rather than by the reference, which is the tell that
the reference had no test for it. Each is now pinned here, in the repo the ports
copy from, so the lesson travels with the spec instead of living in a review
comment.

1. Length rules port wrongly unless the FRAME is pinned — "at least 32
   characters" means different numbers depending on whether a matcher's bound
   includes the 6-character checksum.
2. Fall-through makes a wrong floor INVISIBLE. Once a failing match declines
   instead of erroring, a floor that is too low looks exactly like a floor that
   is right. Only a length pair either side of the boundary can tell them apart.
3. A model comparison is shape-blind by construction, so anything the spec says
   about SERIALIZATION needs its own check or it is decoration. Five
   implementations certified at 104/104 while disagreeing about the bytes they
   emitted.

See `this.i:b3ch32fl`, `this.i:l4b3ld0m`, `this.i:w3aksig`, and the "Corrections
to v17" section of docs/spec-change-log.md.
"""
import re
import sys

import pytest

sys.path.insert(0, ".")

from compliance.model import extract_model  # noqa: E402
from entviz.entropy import (  # noqa: E402
    BECH32_ALPHABET,
    _bech32_hrp_expand,
    _bech32_polymod,
    parse,
)
from entviz.pipeline import render  # noqa: E402


def _bech32(hrp: str, data_chars: int) -> str:
    """A checksum-VALID bech32 string whose data part is exactly ``data_chars``.

    The payload is padded with the zero digit, so the two strings these tests
    compare differ only in length — which is the whole point.
    """
    payload = [0] * (data_chars - 6)
    pm = _bech32_polymod(_bech32_hrp_expand(hrp) + payload + [0] * 6) ^ 1
    chk = [(pm >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + "1" + "".join(BECH32_ALPHABET[d] for d in payload + chk)


# --- Lesson 1 + 2: the floor, and the frame it is measured in ----------------

def test_the_generic_bech32_floor_is_measured_INCLUDING_the_checksum():
    # The frame, pinned as an executable statement rather than a comment. The
    # data part is everything after the separator, checksum included. A port
    # whose matcher bounds only the payload must translate 32 into 26 + 6.
    valid = "cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e"
    data = valid.split("1", 1)[1]
    assert len(data) == 38, "the corpus Cosmos vector's data part, checksum included"
    assert parse(valid).type == "bech32"
    assert len(parse(valid).core) == 32 and len(parse(valid).suffix) == 6


def test_a_31_char_data_part_declines_and_a_32_char_one_matches():
    # THE test the fall-through made necessary. Both strings below carry a VALID
    # polymod, so the checksum cannot be what separates them — only the floor
    # can. Without a pair like this, a floor set too low is indistinguishable
    # from a correct one, because both simply decline for some other reason.
    below = _bech32("ab", 31)
    at = _bech32("ab", 32)
    assert len(below.split("1", 1)[1]) == 31
    assert len(at.split("1", 1)[1]) == 32
    assert parse(below) is None or parse(below).type != "bech32"
    assert parse(at) is not None and parse(at).type == "bech32"


# --- Lesson 2 again: weak signals decline, explicit markers reject ------------

# Inputs whose ONLY scheme signal is a leading character or a reserved digit
# pair. A failing checksum here means "not that scheme", not "that scheme,
# corrupted", so the parser MUST decline and let the input continue.
WEAK_SIGNAL_BAD_CHECKSUM = [
    ("btc-legacy", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb", "BTC"),
    ("lei", "5493001KJTIIGC8Y1R13", "LEI"),
    ("cashaddr-bare", "qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6q", "BCH"),
    # Litecoin legacy. Added after the entviz-go and entviz-java agents each
    # independently discovered this table was short: the corpus has no
    # Litecoin-legacy vector (the `litecoin` vector is the bech32 `ltc1` form),
    # so nothing here or in the corpus exercised the base58check arm. The valid
    # twin is version 0x30 over a fixed hash; this is that address with its last
    # character corrupted.
    ("ltc-legacy", "LKDyUEtTR1HXamkiEphisSiBJu6o3ZPE35", "LTC"),
    ("generic-bech32", "cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363f", "bech32"),
]

# Inputs carrying an unmistakable multi-character marker. A failing checksum
# here really does mean a corrupt instance of that scheme, so rejection stands.
EXPLICIT_MARKER_BAD_CHECKSUM = [
    ("bc1", "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5"),
    ("ltc1", "ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n8"),
    ("bitcoincash:", "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6q"),
    ("eip55", "0x5aaeb6053F3E94C9b9A09f33669435E7Ef1BeAed"),
    # Cardano. `addr1`/`stake1` is named in the rule as an explicit marker and
    # the reference does reject on it, but this table omitted it until the
    # entviz-go agent added the case to its own port and the omission showed up
    # by comparison.
    ("addr1", "addr1qyqqzqsrqszsvpcgpy9qkrqdpc83qygjzv2p29shrqv35xmyv4nxw6rfdf4kc"
              "mtwdac8zunnw36hvamc09a8klra0elsr0jfps"),
]


@pytest.mark.parametrize("name,value,scheme", WEAK_SIGNAL_BAD_CHECKSUM)
def test_a_weak_signal_declines_and_never_claims_the_scheme(name, value, scheme):
    parsed = parse(value)
    assert parsed is not None, f"{name} must still render as SOMETHING"
    assert scheme not in (parsed.type or ""), (
        f"{name} rendered AS {scheme} with a failing checksum — the label must "
        f"report the encoding actually recognized"
    )


@pytest.mark.parametrize("name,value", EXPLICIT_MARKER_BAD_CHECKSUM)
def test_an_explicit_marker_still_rejects(name, value):
    # Guards the correction from over-reaching: it must not turn into "never
    # reject anything".
    with pytest.raises(Exception):
        parse(value)


def test_no_random_value_is_refused_outright():
    # The property the whole correction exists to establish, stated directly.
    # Before it, ~2% of random short values were refused.
    import secrets
    alphabets = {
        "hex": "0123456789abcdef",
        "base58": "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz",
        "base36": "0123456789abcdefghijklmnopqrstuvwxyz",
    }
    refused = []
    for name, alpha in alphabets.items():
        for n in (12, 16, 20, 24, 26, 32, 34, 40, 42):
            for _ in range(120):
                s = "".join(secrets.choice(alpha) for _ in range(n))
                try:
                    parse(s)
                except Exception as exc:
                    refused.append((name, s, type(exc).__name__))
    assert not refused, f"values refused outright: {refused[:5]}"


# --- Lesson 3: the model is shape-blind unless something checks the shape -----

def test_tier_a_records_the_label_serialization():
    # The normative form: marker in a tspan, type text as bare character data.
    model = extract_model(render("0123456789abcdef" * 16))
    assert model["labels"]["top_nodes"] == ["tspan", "chars"]
    assert extract_model(render("550e8400-e29b-41d4-a716-446655440000"))[
        "labels"]["top_nodes"] == ["chars"]


def test_the_serialization_check_actually_CATCHES_the_divergence():
    # A guard that is never shown to fire is a guard nobody can trust. Take a
    # real render, rewrite its label into the wrapped form entviz-js used to
    # emit — same pixels, same text — and assert the model notices. Without this
    # field the two are indistinguishable, which is exactly how five
    # implementations certified while disagreeing about their bytes.
    svg = render("0123456789abcdef" * 16)
    wrapped = re.sub(
        r'(<tspan fill="#a00000" font-weight="bold">\+hash </tspan>)([^<]+)</text>',
        r"\1<tspan>\2</tspan></text>",
        svg,
        count=1,
    )
    assert wrapped != svg, "the rewrite must actually have applied"

    honest, forged = extract_model(svg), extract_model(wrapped)
    # The text is identical — which is why the old model could not tell them apart.
    assert honest["labels"]["top"] == forged["labels"]["top"]
    # The node shape is not.
    assert honest["labels"]["top_nodes"] == ["tspan", "chars"]
    assert forged["labels"]["top_nodes"] == ["tspan", "tspan"]
    assert honest != forged
