from src.text_cleaner import clean_text


def test_basic():
    assert clean_text("  -\u041a\u043b\u044e\u0447-\u0433\u0430\u0435\u0447\u043d\u044b\u0439! (\u0440\u0430\u0437\u043c\u0435\u0440 12)  ") == "\u043a\u043b\u044e\u0447-\u0433\u0430\u0435\u0447\u043d\u044b\u0439 \u0440\u0430\u0437\u043c\u0435\u0440 12"

def test_usb():
    assert clean_text("USB-\u043a\u043b\u044e\u0447") == "usb-\u043a\u043b\u044e\u0447"

def test_only_special():
    assert clean_text("!!!") == ""

def test_only_hyphen():
    assert clean_text("-") == ""

def test_none():
    assert clean_text(None) == ""

def test_empty():
    assert clean_text("") == ""

def test_exclamation_inside():
    assert clean_text("\u041a\u043b\u044e\u0447!!!\u0413\u0430\u0435\u0447\u043d\u044b\u0439") == "\u043a\u043b\u044e\u0447 \u0433\u0430\u0435\u0447\u043d\u044b\u0439"

def test_hyphen_with_spaces():
    assert clean_text("\u043a\u043b\u044e\u0447 - \u0433\u0430\u0435\u0447\u043d\u044b\u0439") == "\u043a\u043b\u044e\u0447 \u0433\u0430\u0435\u0447\u043d\u044b\u0439"

def test_leading_hyphen_digit():
    assert clean_text("-3-\u0431\u043e\u043b\u0442") == "3 \u0431\u043e\u043b\u0442"

def test_double_hyphen():
    assert clean_text("\u041a\u043b\u044e\u0447  --  \u0413\u0430\u0435\u0447\u043d\u044b\u0439") == "\u043a\u043b\u044e\u0447 \u0433\u0430\u0435\u0447\u043d\u044b\u0439"

def test_only_spaces():
    assert clean_text("   ") == ""