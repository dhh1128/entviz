"""
Large-input handling: inputs whose underlying byte length exceeds 64
bytes (>512 bits), or whose tokenization would otherwise exceed the
22-cell budget, are reduced to a head (8 tokens) + 4 middle tokens +
tail (8 tokens), separated by two blank cells when rendered. The
fingerprint is always computed over the full input, so it binds into
every fingerprint-driven channel.

Head/tail are real input entropy (192 bits = 32 hex chars per side, 8
tokens). v6 changed the middle: the 4 middle tokens are now taken from
the middle of the SHA-512 fingerprint (digest bytes 24-35), rendered in
the input's alphabet (see test_v6_fingerprint_middle.py). These tests
assert head/tail content and token counts, which are unchanged.
"""
from entviz.entropy import tokenize, tokenize_entropy
from entviz.fingerprint import compute_fingerprint


def test_small_input_passes_through_unchanged():
    core = "DEADBEEF"  # 8 hex chars → 2 tokens (1 full + 1 partial)
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert not is_truncated
    assert len(tokens) == 2
    # Tokens identical to plain tokenize() for non-truncated inputs.
    assert tokens == tokenize(core, "hex")


def test_uuid_size_input_passes_through():
    # UUID core: 32 hex chars → 6 tokens (5 full + 1 partial)
    core = "550e8400e29b41d4a716446655440000"
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert not is_truncated
    assert len(tokens) == 6


def test_exact_512_bit_input_passes_through():
    # 512 bits = 128 hex chars = 22 tokens (21 full of 6 chars + 1 partial of 2 chars).
    # This is the boundary: at exactly 22 tokens / 64 bytes, no truncation.
    core = "DEADBEEF" * 16  # 128 chars
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert not is_truncated
    assert len(tokens) == 22


def test_above_512_bits_truncates_hex():
    # v4→v5: 576 bits = 144 hex chars; v5 returns 20 tokens (head 8 +
    # middle 4 + tail 8). Blank cells are placed at render time by the
    # median/quartile shift, not by tokenize_entropy.
    core = "DEADBEEF" * 18  # 144 chars
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert is_truncated
    assert len(tokens) == 20


def test_above_512_truncation_keeps_first_and_last_192_bits():
    # v4→v5: head/tail were 256 bits (64 chars hex); v5 shrinks both to
    # 192 bits = 32 chars hex (8 tokens × 6 chars). The middle group
    # of 4 cells now contains fingerprint-sampled slices that are not
    # necessarily all-A or all-C; we only assert head and tail content.
    head = "A" * 48     # > 32 chars so the first 32 are stable
    middle = "B" * 80   # padding for the body
    tail = "C" * 48
    core = head + middle + tail  # 176 hex chars = 30 tokens
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert is_truncated
    assert len(tokens) == 20
    # First 8 tokens — all 'A'.
    for i in range(8):
        assert set(tokens[i].text) == {"A"}, f"head token {i} text {tokens[i].text!r}"
    # Last 8 tokens (indices 12..19) — all 'C'.
    for j in range(8):
        assert set(tokens[12 + j].text) == {"C"}, (
            f"tail token {j} text {tokens[12 + j].text!r}"
        )


def test_truncated_indices_are_renumbered_0_to_19():
    # v4→v5: token range shrinks from 0..21 to 0..19; two extra cells (8
    # blanks are inserted by the pipeline's median/quartile shift.
    core = "DEADBEEF" * 18
    tokens, _ = tokenize_entropy(core, "hex")
    assert [t.index for t in tokens] == list(range(20))


def test_base64_input_above_threshold_yields_20_tokens():
    # v4→v5: base64 uses 6 bits per char; 192-bit head/tail = 32 chars
    # each (8 tokens × 4 chars). A 200-base64-char input is well over
    # the 64-byte threshold; expect 20 tokens.
    head = "A" * 32
    middle = "C" * 136
    tail = "Z" * 32
    core = head + middle + tail  # 200 chars
    tokens, is_truncated = tokenize_entropy(core, "base64")
    assert is_truncated
    assert len(tokens) == 20
    # First 8 tokens all 'A'; last 8 all 'Z'.
    for i in range(8):
        assert set(tokens[i].text) == {"A"}
    for j in range(8):
        assert set(tokens[12 + j].text) == {"Z"}


def test_inputs_sharing_head_and_tail_but_differing_middle_now_differ_in_text():
    # In v4 the truncated tokens were byte-identical for two inputs
    # sharing head-256 and tail-256 (the F5 finding). v6 makes the middle
    # group fingerprint-derived, so it differs whenever the fingerprint
    # does — i.e. on ANY input change — and the TEXT channel discriminates
    # the two inputs. (v5 used body slices; this is now guaranteed, not
    # probabilistic.)
    head = "DEADBEEF" * 8   # 64 hex chars (covers v5's first 32 plus margin)
    tail = "FEEDFACE" * 8   # 64 hex chars
    core_a = head + ("A" * 64) + tail  # 192 chars = 96 bytes
    core_b = head + ("B" * 64) + tail
    tokens_a, _ = tokenize_entropy(core_a, "hex")
    tokens_b, _ = tokenize_entropy(core_b, "hex")
    # Head and tail tokens match.
    for i in range(8):
        assert tokens_a[i].text == tokens_b[i].text
    for j in range(8):
        assert tokens_a[12 + j].text == tokens_b[12 + j].text
    # Middle tokens MUST differ on at least one cell — that's the v5
    # text-channel improvement F5 demanded.
    middle_a = [t.text for t in tokens_a[8:12]]
    middle_b = [t.text for t in tokens_b[8:12]]
    assert middle_a != middle_b, (
        "fingerprint-derived middle must differ when inputs differ"
    )
    # Fingerprints differ (avalanche is preserved).
    assert compute_fingerprint(core_a) != compute_fingerprint(core_b)


def test_token_count_never_exceeds_22():
    # v4→v5: post-truncation token count is now exactly 20 (was 22).
    # Stress test: very large input.
    core = "DEADBEEF" * 1000  # 8000 chars = ~1333 tokens
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert is_truncated
    assert len(tokens) == 20
