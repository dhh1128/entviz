import pytest
from entviz.entropy import tokenize, Token

def test_tokenize_hex():
    tokens = tokenize("ABCDEF123456", "hex")
    assert len(tokens) == 2
    assert tokens[0].text == "ABCDEF"
    assert tokens[0].quant == 0xABCDEF
    assert tokens[1].text == "123456"
    assert tokens[1].quant == 0x123456

def test_tokenize_base64():
    # 'A' is 0, '/' is 63
    tokens = tokenize("AAAA////", "base64")
    assert len(tokens) == 2
    assert tokens[0].quant == 0x000000
    assert tokens[1].quant == 0xFFFFFF

def test_tokenize_repetition():
    # "AB" in hex is 0xAB (8 bits: 10101011)
    # 8 bits -> 16 bits (0xABAB) -> 24 bits (0xABABAB)
    tokens = tokenize("AB", "hex", token_len=2) 
    assert tokens[0].quant == 0xABABAB

def test_tokenize_base58():
    # '1' is 0 in BASE58_ALPHABET
    tokens = tokenize("1111", "base58")
    assert tokens[0].quant == 0
    
    # 'z' is 57 (index 57)
    # 4 chars * 6 bits = 24 bits. No repetition needed if treated as 6-bit chars.
    tokens = tokenize("zzzz", "base58")
    # index 57 is 0x39
    # 0x39 << 18 | 0x39 << 12 | 0x39 << 6 | 0x39
    expected = (57 << 18) | (57 << 12) | (57 << 6) | 57
    assert tokens[0].quant == expected
