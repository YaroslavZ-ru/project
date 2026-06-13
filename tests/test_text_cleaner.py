from src.text_cleaner import clean_text


def test_basic():
    assert clean_text("  -Ключ-гаечный! (размер 12)  ") == "ключ-гаечный размер 12"

def test_usb():
    assert clean_text("USB-ключ") == "usb-ключ"

def test_only_special():
    assert clean_text("!!!") == ""

def test_only_hyphen():
    assert clean_text("-") == ""

def test_none():
    assert clean_text(None) == ""

def test_empty():
    assert clean_text("") == ""

def test_exclamation_inside():
    assert clean_text("Ключ!!!Гаечный") == "ключ гаечный"

def test_hyphen_with_spaces():
    assert clean_text("ключ - гаечный") == "ключ гаечный"

def test_leading_hyphen_digit():
    assert clean_text("-3-болт") == "3 болт"

def test_double_hyphen():
    assert clean_text("Ключ  --  Гаечный") == "ключ гаечный"

def test_only_spaces():
    assert clean_text("   ") == ""