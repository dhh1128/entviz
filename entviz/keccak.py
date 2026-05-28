"""
Minimal pure-Python Keccak-256 (the original Keccak, NOT NIST SHA3-256).

Why this file exists: EIP-55 Ethereum address checksums are computed
with Keccak-256, which uses the original Keccak padding (`0x01` ... `0x80`).
NIST standardized SHA3-256 later with a different padding (`0x06` ... `0x80`),
so `hashlib.sha3_256` produces a DIFFERENT digest and CANNOT be used here.
A prior implementation in this codebase made exactly that mistake, which is
part of what motivated this rewrite (see review F7b and `this.i:3ip55rj1`).

The implementation below is a from-scratch transcription of the Keccak-f[1600]
permutation as specified in the original Keccak reference (Bertoni, Daemen,
Peeters, Van Assche). Cross-checked against the EIP-55 spec's published test
vectors (e.g. `0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed`) — see
`tests/test_f7_eip55.py::test_keccak256_vectors_eip55`.

No third-party dependency is added; vendoring keeps entviz dependency-light
(per AGENTS.md / project policy).
"""

# Round constants for Keccak-f[1600]: 24 rounds, one 64-bit constant each.
_RC = (
    0x0000000000000001, 0x0000000000008082,
    0x800000000000808a, 0x8000000080008000,
    0x000000000000808b, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009,
    0x000000000000008a, 0x0000000000000088,
    0x0000000080008009, 0x000000008000000a,
    0x000000008000808b, 0x800000000000008b,
    0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080,
    0x000000000000800a, 0x800000008000000a,
    0x8000000080008081, 0x8000000000008080,
    0x0000000080000001, 0x8000000080008008,
)

# Rotation offsets for the rho step. Indexed as _ROT[y][x] — the outer
# index is the row y, the inner is the column x. (Keccak's spec table
# lists rho offsets in an (x,y) matrix; the row-major Python layout here
# corresponds to fixing y and varying x along each tuple.)
_ROT = (
    ( 0,  1, 62, 28, 27),  # y = 0: x = 0..4
    (36, 44,  6, 55, 20),  # y = 1
    ( 3, 10, 43, 25, 39),  # y = 2
    (41, 45, 15, 21,  8),  # y = 3
    (18,  2, 61, 56, 14),  # y = 4
)

_MASK64 = 0xFFFFFFFFFFFFFFFF


def _rotl64(x, n):
    n &= 63
    if n == 0:
        return x & _MASK64
    return ((x << n) | (x >> (64 - n))) & _MASK64


def _keccak_f1600(state):
    """In-place 24-round Keccak-f[1600] permutation on a 5x5 lane array."""
    for rnd in range(24):
        # Theta
        C = [state[x][0] ^ state[x][1] ^ state[x][2] ^ state[x][3] ^ state[x][4] for x in range(5)]
        D = [C[(x - 1) % 5] ^ _rotl64(C[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x][y] ^= D[x]

        # Rho + Pi
        B = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                B[y][(2 * x + 3 * y) % 5] = _rotl64(state[x][y], _ROT[y][x])

        # Chi
        for x in range(5):
            for y in range(5):
                state[x][y] = B[x][y] ^ ((~B[(x + 1) % 5][y]) & B[(x + 2) % 5][y]) & _MASK64

        # Iota
        state[0][0] ^= _RC[rnd]


def keccak256(data: bytes) -> bytes:
    """
    Return the 32-byte Keccak-256 digest of `data`.

    This is the original Keccak with `0x01` domain-separation byte (NOT the
    `0x06` byte used by NIST SHA3-256). Rate = 1088 bits = 136 bytes;
    capacity = 512 bits; output = 256 bits.
    """
    rate_bytes = 136
    state = [[0] * 5 for _ in range(5)]

    # Absorb full rate-sized blocks.
    offset = 0
    n = len(data)
    while n - offset >= rate_bytes:
        _absorb_block(state, data, offset, rate_bytes)
        _keccak_f1600(state)
        offset += rate_bytes

    # Pad the final (possibly empty) block: 0x01 ... 0x80.
    last = bytearray(data[offset:])
    last.append(0x01)
    while len(last) < rate_bytes:
        last.append(0x00)
    last[-1] |= 0x80
    _absorb_block(state, bytes(last), 0, rate_bytes)
    _keccak_f1600(state)

    # Squeeze 32 bytes (one rate-sized squeeze is plenty: 32 < 136).
    out = bytearray()
    for i in range(32):
        lane_index = i // 8
        x = lane_index % 5
        y = lane_index // 5
        byte_in_lane = i % 8
        out.append((state[x][y] >> (8 * byte_in_lane)) & 0xFF)
    return bytes(out)


def _absorb_block(state, data: bytes, offset: int, rate_bytes: int) -> None:
    """XOR `rate_bytes` bytes of `data` (starting at `offset`) into `state`."""
    for i in range(rate_bytes):
        lane_index = i // 8
        x = lane_index % 5
        y = lane_index // 5
        byte_in_lane = i % 8
        state[x][y] ^= (data[offset + i] & 0xFF) << (8 * byte_in_lane)
