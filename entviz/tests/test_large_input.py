"""
v2 large-input handling: inputs whose tokenization would exceed 22 tokens
are truncated to the first ~256 bits and the last ~256 bits, with a
logical blank-cell separator. The fingerprint is always computed over
the full input, so the truncated middle still binds into every
fingerprint-driven channel.
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
    # This is the boundary: at exactly 22 tokens, no truncation should occur.
    core = "DEADBEEF" * 16  # 128 chars
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert not is_truncated
    assert len(tokens) == 22


def test_above_512_bits_truncates_hex():
    # 576 bits = 144 hex chars = 24 tokens > 22, so truncate.
    core = "DEADBEEF" * 18  # 144 chars
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert is_truncated
    # First 256 bits (64 hex chars) yields 11 tokens (10 full + 1 partial of 4 chars).
    # Last 256 bits (64 hex chars) yields 11 tokens.
    # Total: 22 tokens.
    assert len(tokens) == 22


def test_above_512_truncation_keeps_first_256_and_last_256_bits():
    # Build a core whose first/last 64 chars are distinguishable from the middle.
    head = "AAAAAA" * 11  # 66 chars but we'll only use first 64
    # Actually use a clearer structure: 64 'A' chars head, middle of 'B' chars,
    # 64 'C' chars tail. Total > 128 chars to force truncation.
    head = "A" * 64
    middle = "B" * 32
    tail = "C" * 64
    core = head + middle + tail  # 160 hex chars = 27 tokens
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert is_truncated
    assert len(tokens) == 22
    # First 11 tokens should all be made of 'A' chars; last 11 of 'C' chars.
    for i in range(11):
        assert set(tokens[i].text) == {"A"}, f"head token {i} text was {tokens[i].text!r}"
    for j in range(11):
        assert set(tokens[11 + j].text) == {"C"}, f"tail token {j} text was {tokens[11 + j].text!r}"


def test_truncated_indices_are_renumbered_0_to_21():
    core = "DEADBEEF" * 18
    tokens, _ = tokenize_entropy(core, "hex")
    assert [t.index for t in tokens] == list(range(22))


def test_base64_input_above_threshold_truncates_at_43_chars_per_side():
    # base64 uses 6 bits per char; ceil(256/6) = 43 chars per side.
    # An input of 100 base64 chars = 25 tokens, well over 22.
    head = "A" * 43
    middle = "C" * 14
    tail = "Z" * 43
    core = head + middle + tail  # 100 chars
    tokens, is_truncated = tokenize_entropy(core, "base64")
    assert is_truncated
    assert len(tokens) == 22
    # First 11 tokens should be all 'A'; last 11 all 'Z'.
    for i in range(11):
        assert set(tokens[i].text) == {"A"}
    for j in range(11):
        assert set(tokens[11 + j].text) == {"Z"}


def test_inputs_sharing_ends_but_differing_middle_have_same_truncated_tokens():
    # This is the failure mode the fingerprint exists to detect: two inputs
    # with identical first/last 256 bits but different middles produce
    # identical truncated tokens (i.e., identical *displayed text*), but
    # the fingerprint must differ.
    head = "DEADBEEF" * 8   # 64 hex chars
    tail = "FEEDFACE" * 8   # 64 hex chars
    core_a = head + ("A" * 32) + tail  # 160 chars
    core_b = head + ("B" * 32) + tail  # 160 chars
    tokens_a, _ = tokenize_entropy(core_a, "hex")
    tokens_b, _ = tokenize_entropy(core_b, "hex")
    # Truncated tokens are identical: text channel cannot distinguish.
    assert [(t.text, t.quant) for t in tokens_a] == [(t.text, t.quant) for t in tokens_b]
    # But fingerprints differ — the avalanche is preserved.
    assert compute_fingerprint(core_a) != compute_fingerprint(core_b)


def test_token_count_never_exceeds_22():
    # Stress test: very large input. After truncation, must be exactly 22.
    core = "DEADBEEF" * 1000  # 8000 chars = ~1333 tokens
    tokens, is_truncated = tokenize_entropy(core, "hex")
    assert is_truncated
    assert len(tokens) == 22
