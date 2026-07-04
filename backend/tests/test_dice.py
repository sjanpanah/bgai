from engine.state import Dice


def test_roll_values_in_range():
    dice = Dice(seed=1)
    for _ in range(100):
        d1, d2 = dice.roll()
        assert 1 <= d1 <= 6
        assert 1 <= d2 <= 6


def test_same_seed_same_sequence():
    a = Dice(seed=42)
    b = Dice(seed=42)
    assert [a.roll() for _ in range(20)] == [b.roll() for _ in range(20)]


def test_different_seed_different_sequence():
    a = Dice(seed=1)
    b = Dice(seed=2)
    assert [a.roll() for _ in range(20)] != [b.roll() for _ in range(20)]


def test_no_seed_still_works():
    dice = Dice()
    d1, d2 = dice.roll()
    assert 1 <= d1 <= 6
    assert 1 <= d2 <= 6
