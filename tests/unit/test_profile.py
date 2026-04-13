from utils.validators import validate_age, validate_hours_per_week, validate_pubg_name


def test_validate_pubg_name():
    assert validate_pubg_name("ProPlayer_123")
    assert validate_pubg_name("account.1234567890abcdef1234567890")
    assert not validate_pubg_name("a")
    assert not validate_pubg_name("bad name")


def test_validate_age():
    assert validate_age("13") == (True, 13)
    assert validate_age("12") == (False, 12)
    assert validate_age("abc") == (False, None)


def test_validate_hours_per_week():
    assert validate_hours_per_week("1") == (True, 1)
    assert validate_hours_per_week("168") == (True, 168)
    assert validate_hours_per_week("169") == (False, 169)
