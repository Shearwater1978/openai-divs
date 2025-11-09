from modules.money_utils import money

def test_money_round_half_even():
    assert money(2.345) == 2.34  # 4 is even
    assert money(2.355) == 2.36  # 5 rounds to even (6)
