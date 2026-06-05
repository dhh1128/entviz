import pytest
from entviz.entropy import Token, get_median_token, get_quartile_tokens

@pytest.fixture
def spec_tokens():
    # Based on the spec example (Table in Steps 5 and 6)
    # Using '79rX' to match the quartile table exactly.
    texts = ["Ead-", "k992", "cxJ3", "29v4", "f_G8", "23v9", "BA4m", "79rX"]
    return [Token(text, i, 0) for i, text in enumerate(texts)]

def test_median_token_spec(spec_tokens):
    # Median should be BA4m (index 6)
    median = get_median_token(spec_tokens)
    assert median.text == "BA4m"
    assert median.index == 6

def test_quartile_tokens_spec(spec_tokens):
    # Quartiles should be: Ead-, cxJ3, f_G8, 79rX
    quartiles = get_quartile_tokens(spec_tokens)
    assert len(quartiles) == 4
    assert quartiles[0].text == "Ead-"
    assert quartiles[1].text == "cxJ3"
    assert quartiles[2].text == "f_G8"
    assert quartiles[3].text == "79rX"

def test_median_token_odd_count():
    tokens = [
        Token("A", 0, 0),
        Token("B", 1, 0),
        Token("C", 2, 0)
    ]
    # Sorted: A, B, C. Median is B.
    assert get_median_token(tokens).text == "B"

def test_quartile_tokens_non_multiple_of_4():
    # 5 tokens. q_size = ceil(5/4) = 2.
    # Sorted mirrored: A, B, C, D, E.
    # Indices: 0, 2, 4, 6 (out of bounds)
    # Actually for 5 tokens:
    # 0, 1 (1st q)
    # 2, 3 (2nd q)
    # 4 (3rd q)
    # Padding items (4th q)
    tokens = [Token(c, i, 0) for i, c in enumerate("ABCDE")]
    quartiles = get_quartile_tokens(tokens)
    assert quartiles[0].text == "A"
    assert quartiles[1].text == "C"
    assert quartiles[2].text == "E"
    # The 4th quartile index is 3 * q_size = 6, which is >= count (5), so the
    # padding-at-bottom rule yields no token: get_quartile_tokens returns None
    # for that slot (the pipeline then draws no quartile mark there).
    assert quartiles[3] is None
