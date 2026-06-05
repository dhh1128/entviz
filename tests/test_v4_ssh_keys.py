"""
v4 SSH public-key parser: detect specific key types (ed25519, rsa, dss,
ecdsa-sha2-nistp256/384/521) by their fixed base64 prefix, and detect
the optional trailing space-separated comment as a suffix.

Wire format (base64-decoded): length(4 BE) + type_string + length + field1
(+ length + field2 + ...). For each known type, the base64 prefix bytes
are structural overhead (length prefix + type-string bytes), and for
ssh-rsa we additionally fold in the second field (the small public
exponent, almost always 65537) since its value is the same for ~all
real-world RSA keys and carries no per-key entropy.

For ecdsa-sha2-nistpXXX we fold in the curve-name field too — the curve
name is fully redundant with the type string ("nistp256" appears in
both), so visually it's pure overhead.

Real SSH public-key lines have the form:
    <type-string> <base64-payload> [<comment>]
The parser is fed the post-type-string text (the parse() pipeline strips
the leading "<type> " when it would otherwise fail to match), so the
parser sees `<base64>` or `<base64> <comment>` and the comment is the
parser's `suffix`.
"""
from entviz.entropy import parse_ssh_key, parse, BASE64


# Real-shape test vectors. These are well-known test vectors / canonical
# examples, not production keys.
ED25519_PAYLOAD = "AAAAC3NzaC1lZDI1NTE5AAAAIDtJVH9hM+2DyhmgRZBfeIDoVqCTbXY+0nKlS5pTkkXY"
RSA_PAYLOAD = (
    "AAAAB3NzaC1yc2EAAAADAQABAAABgQDSD+oM4kLidAptE5pjRA8OBIWNysc9reQJjK"
    "egek2jATA3bSvKdq/wdQtpbihEx5OlKMo//V/8QpAIjCSsBaMb6G/e/D5kC9wCjnYJ"
    "J68+34L+H5Fx1Ofuiz3BidgssINw/qbV0u1vrCop+ggs6lkl+pIwa+9kPriD9xdowC"
    "OQABMVl4todcojY8gZK/Zs5XTwKi9Z8MRS/37FEPxlvpRExMmQU8v2tnP/TDqhR13N"
    "SyCZWqiH2ojMNDm2jWR+W65gIjFz4kNsu4EaSNOfKY4U7VRBLXg7om3pvIoarhBFMZ"
    "vTPQ9FqJU/08BJ/A1tCjCIAY0+zGAAvfRHQt5R2wZXl83n9Xh+9IukW5r/pynpdLx1"
    "+WyAOKLxIUKflTWaIcYKBqmfaxz64Gm2lDbF0+9r/0Xf//P8TFDWFo9bo4loIukgjt"
    "wQmp8Kn6ngEKj8gS3vLApZ3wN18q3emtglyQEmO+9VXckK4NPOqAzwOu7rQbr7oEPS"
    "6HrnY3PKe9JD570="
)
DSS_PAYLOAD = (
    "AAAAB3NzaC1kc3MAAACBAKGcEm/5P2PSlg6+Vj8NTlR4elcBzhVgegS3zgpJ7WdzhC"
    "857ggkAs9M/KHQVcEDbg3BiRk2r4cRMqPUZ2i61u9lL63WuhkY/eaMdkqR7Df5ZdoR"
    "sduKP0ENpciAFhHnaUlvDbujDPSxSNRJq5+zQuzoJxIJRbLCbAnp/jPBAqWTAAAAFQ"
    "DjDPh4NhNLDneMFFPSDrLC7NJR1QAAAIBDfQ+Yuufm2W19Oafm6ei/XyTskVYwx/rP"
    "p+H/m3Jczt47DzTsjzzVLgQS2GPLcu3Ms6XLP9/ko4aEK2dgTox1SV4T//NOrSIgJM"
    "3u/UbXaacY9g3C9wAHwOKV9iondUL+Qn+pJ/fphLStqmyIpXqmjXKqT+gv1uJFQZuP"
    "q1oh1QAAAIAxbOZot7HRRA9QX7kayXv7o00w9St7LrxhOjIAudU6IBsigqpNeIPXcK"
    "74mOotZ2OhMLMfggsUZUkNQ1oMH+isJF7gEVMcatdPpTCa2AFQFKJRWpVNmKGueQ44"
    "Sl5l4mrNfSdW1IOf7Z5pHKzjrSgJGO9KRcm1N9sYow7GCEdP9Q=="
)
ECDSA_P256_PAYLOAD = (
    "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBNSBA0Md9M/Cwp"
    "0J32Rvk/aiElw77t6l9YQbMmJSP4PfybRxeGP4fqsrIvr6ckdRms5N8Bp/kvug/iAg"
    "X6OK59E="
)


def test_ed25519_type_in_parser_type_name():
    p = parse_ssh_key(ED25519_PAYLOAD)
    assert p is not None
    assert "ed25519" in p.type.lower()
    assert p.alphabet == BASE64


def test_ed25519_prefix_includes_key_length_field_bytes():
    """The ed25519 prefix is 24 base64 chars = 18 bytes = the 15-byte
    type-string field PLUS the first 3 bytes of the key-length field
    (0x000000, the high bytes of the always-32 key length, encoded as
    `AAAA`). This sweeps the constant structural prefix-zero bytes off
    the front of the core so the cells start as close to pure entropy
    as base64 alignment allows. The remaining 4th key-length byte
    (0x20) is the only structural data leaking into the first cell."""
    p = parse_ssh_key(ED25519_PAYLOAD)
    assert p.prefix == "AAAAC3NzaC1lZDI1NTE5AAAA"
    assert p.prefix + p.core == ED25519_PAYLOAD


def test_ed25519_core_does_not_start_with_aaaa():
    """With the extended prefix, the core no longer leads with the
    `AAAA` structural-zero cell that would otherwise render identically
    across all ed25519 keys. The very first character is still 'I' (the
    base64 encoding of the high 6 bits of the constant 0x20 key-length
    byte), but the next 3 characters of the first cell encode the first
    16 bits of the actual ed25519 key, so the cell varies per-key."""
    p = parse_ssh_key(ED25519_PAYLOAD)
    assert not p.core.startswith("AAAA"), (
        f"core still leads with structural AAAA: {p.core[:8]!r}"
    )
    assert p.core[0] == "I"  # encodes high 6 bits of 0x20


def test_rsa_prefix_includes_exponent():
    """For ssh-rsa, the prefix begins with the type-string field and the
    exponent field (`AAAAB3NzaC1yc2EAAAADAQAB`, 24 chars), then extends
    4 more chars to consume 3 high bytes of the modulus-length field."""
    p = parse_ssh_key(RSA_PAYLOAD)
    assert "rsa" in p.type.lower()
    assert p.prefix.startswith("AAAAB3NzaC1yc2EAAAADAQAB")
    assert len(p.prefix) == 28
    assert p.prefix + p.core == RSA_PAYLOAD


def test_dss_prefix():
    p = parse_ssh_key(DSS_PAYLOAD)
    assert "dss" in p.type.lower() or "dsa" in p.type.lower()
    # ssh-dss type-string-portion (no exponent equivalent for DSA).
    assert p.prefix == "AAAAB3NzaC1kc3M"
    assert p.prefix + p.core == DSS_PAYLOAD


def test_ecdsa_p256_prefix_includes_curve_name_and_key_length():
    """For ecdsa-sha2-nistpXXX, the prefix folds in the curve-name field
    (`nistp256`, redundant with the type string) AND the always-constant
    4-byte key-length field (= 65 for nistp256), giving a 52-char clean
    cell-aligned prefix with no entropy leak."""
    p = parse_ssh_key(ECDSA_P256_PAYLOAD)
    assert "256" in p.type
    assert "ecdsa" in p.type.lower()
    assert p.prefix == "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABB"
    assert p.prefix + p.core == ECDSA_P256_PAYLOAD


def test_ssh_key_prefix_lengths_distinguish_types():
    """Each key type produces a distinct prefix length, so the visual
    label can show how much of the input is overhead."""
    e = parse_ssh_key(ED25519_PAYLOAD).prefix
    r = parse_ssh_key(RSA_PAYLOAD).prefix
    d = parse_ssh_key(DSS_PAYLOAD).prefix
    c = parse_ssh_key(ECDSA_P256_PAYLOAD).prefix
    # All distinct
    assert len({e, r, d, c}) == 4
    # ed25519 = 24 (type-string + first 3 of 4 key-length bytes)
    assert len(e) == 24
    # rsa = 28 (24-char structural match + 4 more chars covering 3 of 4
    # modulus-length bytes; the 4th byte and modulus enter the core)
    assert len(r) == 28
    # dss is 15
    assert len(d) == 15
    # ecdsa-p256 = 52 (curve-specific full structural prefix including
    # the always-constant 4-byte key-length field 0x00000041)
    assert len(c) == 52


def test_rsa_prefix_extends_into_modulus_length_field():
    """The ssh-rsa prefix grows past the exponent field to also cover
    the high 3 bytes of the 4-byte modulus-length field. Those high
    bytes are reliably 0x00 0x00 0x?? (where ?? depends on key size:
    0x00 for 1024-bit, 0x01 for 2048-3072-bit, 0x02 for 4096-bit, etc).
    Pulling them into the prefix prevents the first cell from rendering
    as the all-structural `AAAB`/`AAAA` pattern. The 4th modulus-length
    byte does leak into the first core cell, but the rest of that cell
    is the actual modulus's high bits."""
    p = parse_ssh_key(RSA_PAYLOAD)
    assert p.prefix.startswith("AAAAB3NzaC1yc2EAAAADAQAB")  # 24-char structural match
    assert len(p.prefix) == 28
    assert not p.core.startswith("AAA"), (
        f"core still leads with structural AAA: {p.core[:8]!r}"
    )


def test_ecdsa_p256_prefix_captures_full_key_length_field():
    """For ecdsa-nistpXXX the structural prefix has a clean
    52-char alignment: 39 bytes = type-string-field (23) + curve-name-
    field (12) + key-length-field (4) → exactly 52 base64 chars with
    no entropy leak. Each curve has its own 52-char constant prefix
    (the key-length encoding differs per curve)."""
    p = parse_ssh_key(ECDSA_P256_PAYLOAD)
    assert p.prefix == "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABB"
    assert not p.core.startswith("AAA"), (
        f"core still leads with structural AAA: {p.core[:8]!r}"
    )


def test_ssh_key_with_type_and_comment_via_parse():
    """The full openssh-format line: `<type> <base64> <comment>`. parse()
    consumes the leading type and the trailing comment. The comment is a
    FREE annotation (not a checksum/derivation, freely variable while the
    key is fixed), so it is dropped — suffix is None. See this.i:sufxbind.
    The leading type is consumed (not in prefix/core/suffix)."""
    line = f"ssh-ed25519 {ED25519_PAYLOAD} user@example.com"
    p = parse(line)
    assert p is not None
    assert "ed25519" in p.type.lower()
    assert p.suffix is None
    # Core + prefix still equal the base64 payload.
    assert p.prefix + p.core == ED25519_PAYLOAD


def test_ssh_comment_does_not_affect_rendering():
    """The same key with different comments is the same value → the VISUAL
    entviz is identical (the free comment is dropped, not rendered). Only the
    informational `data-input-bytes` metadata reflects the literal input
    length, so it is normalized out of the comparison. See this.i:sufxbind."""
    import re
    from entviz.pipeline import render
    norm = lambda s: re.sub(r' data-input-bytes="\d+"', "", s)
    a = render(f"ssh-ed25519 {ED25519_PAYLOAD} alice@host")
    b = render(f"ssh-ed25519 {ED25519_PAYLOAD} bob@elsewhere")
    assert norm(a) == norm(b)


def test_ssh_key_with_type_no_comment_via_parse():
    """`<type> <base64>` with no trailing comment → suffix is None."""
    line = f"ssh-ed25519 {ED25519_PAYLOAD}"
    p = parse(line)
    assert p is not None
    assert p.suffix is None


def test_ssh_key_payload_only_no_comment_via_parse():
    """Bare base64 payload (no leading type, no comment) → still parses,
    suffix None."""
    p = parse(ED25519_PAYLOAD)
    assert p is not None
    assert "ed25519" in p.type.lower()
    assert p.suffix is None


def test_ssh_key_body_is_entropy_for_ed25519():
    """After the extended 24-char prefix sweeps the 3 high bytes of the
    key-length field off the front, the core encodes 33 bytes: the
    leftover 4th key-length byte (0x20) + 32-byte key. 33 bytes → 44
    base64 chars."""
    p = parse_ssh_key(ED25519_PAYLOAD)
    assert len(p.core) == 44


def test_ssh_key_body_for_rsa_starts_at_modulus_length_prefix():
    """The core for ssh-rsa starts at the modulus length prefix (i.e.
    everything from the exponent onward has been folded into `prefix`)."""
    p = parse_ssh_key(RSA_PAYLOAD)
    # The modulus for a 3072-bit RSA key is 384 bytes; with a 4-byte
    # length prefix and a leading 0x00 sign byte that's 389 bytes →
    # base64 length is ceil(389/3)*4 = 520. The exact length depends on
    # the sample, so we just assert the core has substantial size and
    # doesn't start with the exponent bytes.
    assert not p.core.startswith("AAAADAQAB")
    assert len(p.core) > 100
