"""
v4 Ethereum detection tightening: a 40-hex-char input is recognized as
Ethereum ONLY when there's an explicit signal beyond mere length. Plain
single-case hex of any length (including 40) is just hex, not Ethereum.

Signals that promote a 40-hex string to Ethereum:
  - leading "0x" / "0X" prefix
  - EIP-55-style mixed case (at least one uppercase AND one lowercase
    hex letter; digits don't count toward either)
"""
from entviz.entropy import parse


def test_0x_prefix_with_40_hex_is_ethereum():
    """The canonical Ethereum address form."""
    p = parse("0x742d35cc6634c0532925a3b844bc454e4438f44e")
    assert p is not None
    assert p.type == "ETH"


def test_0x_prefix_with_40_hex_uppercase_is_ethereum():
    """Uppercase hex with 0x prefix is still Ethereum."""
    p = parse("0X742D35CC6634C0532925A3B844BC454E4438F44E")
    assert p is not None
    assert p.type == "ETH"


def test_eip55_mixed_case_without_prefix_is_ethereum():
    """40 hex chars with EIP-55 mixed-case checksum, no prefix → Ethereum."""
    p = parse("742d35Cc6634C0532925a3b844Bc454e4438f44e")
    assert p is not None
    assert p.type == "ETH"


def test_40_hex_all_lowercase_no_prefix_is_NOT_ethereum():
    """A plain 40-char hex blob in single-case, no prefix → hex, not
    Ethereum. Disambiguates random hex from address."""
    p = parse("742d35cc6634c0532925a3b844bc454e4438f44e")
    assert p is not None
    assert p.type == "hex"


def test_40_hex_all_uppercase_no_prefix_is_NOT_ethereum():
    """Pure-uppercase 40-char hex, no prefix → hex, not Ethereum."""
    p = parse("742D35CC6634C0532925A3B844BC454E4438F44E")
    assert p is not None
    assert p.type == "hex"


def test_0x_prefix_with_non_40_length_is_plain_hex():
    """0x prefix with a non-40-char body → plain hex (with 0x prefix),
    not Ethereum. Confirms the 0x prefix alone is NOT an Ethereum signal."""
    # 8 hex chars
    p = parse("0xdeadbeef")
    assert p is not None
    assert p.type == "hex"
    # 32 hex chars (private key / tx hash sort of length, but not address)
    p = parse("0xdeadbeefdeadbeefdeadbeefdeadbeef")
    assert p is not None
    assert p.type == "hex"
    # 64 hex chars
    p = parse("0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
    assert p is not None
    assert p.type == "hex"


def test_short_mixed_case_hex_is_not_ethereum():
    """Mixed case alone is not enough — must also be 40 chars."""
    p = parse("DeadBeef")
    assert p is not None
    assert p.type == "hex"


def test_long_mixed_case_hex_is_not_ethereum():
    """64-char mixed-case hex (e.g. an Ethereum tx hash) is plain hex —
    Ethereum-specific recognition is reserved for addresses (40 chars).
    Tx hashes and private keys are 64 hex chars but indistinguishable
    from generic 64-char crypto blobs."""
    p = parse("DeadBeefDeadBeefDeadBeefDeadBeefDeadBeefDeadBeefDeadBeefDeadBeef")
    assert p is not None
    assert p.type == "hex"


def test_ethereum_core_includes_all_40_hex_chars():
    """The full 40-char address body sits in `core` (no suffix split).
    Previously the parser carved off the last 8 chars into `suffix` as if
    they were a separable checksum — but Ethereum's EIP-55 checksum is
    the case pattern of the entire 40 chars, not a trailing slice."""
    p = parse("0x742d35cc6634c0532925a3b844bc454e4438f44e")
    assert p is not None
    # core should be the full 40 hex chars (in EIP-55 mixed case)
    assert len(p.core) == 40
    # suffix should be empty (or None)
    assert not p.suffix


def test_two_ethereums_differing_in_last_8_chars_produce_different_cores():
    """Regression: under the old 32/8 split, addresses differing only in
    the last 8 chars produced identical `core` values, which meant their
    entvizes were identical too. With the fix, the full address is in
    `core` and they diverge."""
    a = parse("0x742d35cc6634c0532925a3b844bc454e44380000")
    b = parse("0x742d35cc6634c0532925a3b844bc454e4438ffff")
    assert a.core != b.core
