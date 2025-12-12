import pytest
from calculator import calculate_commission


class TestCalculateCommission:

    @pytest.mark.parametrize(
        "amount, expected",
        [
            (100, 50.0),
            (1000, 50.0),
            (1001, 100.0),
            (20000, 100.0),
            (20001, 400.01),
            (40000, 600.0),
            (40001, 500.0),
            (50000, 500.0),
        ]
    )
    def test_commission_positive(self, amount, expected):
        assert calculate_commission(amount) == expected

    @pytest.mark.parametrize(
        "invalid_amount",
        [99, 50001, -10]
    )
    def test_invalid_amount_raises_value_error(self, invalid_amount):
        with pytest.raises(ValueError):
            calculate_commission(invalid_amount)

    @pytest.mark.parametrize(
        "invalid_type",
        ["abc", 10.5, None]
    )
    def test_invalid_type_raises_type_error(self, invalid_type):
        with pytest.raises(TypeError):
            calculate_commission(invalid_type)
