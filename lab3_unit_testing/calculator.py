def calculate_commission(amount: int) -> float:
    """
    Рассчитывает комиссию для денежного перевода.

    :param amount: сумма перевода (100–50000)
    :return: комиссия
    """
    if not isinstance(amount, int):
        raise TypeError("Сумма должна быть целым числом")

    if amount < 100 or amount > 50000:
        raise ValueError("Сумма перевода должна быть от 100 до 50 000 руб.")

    if amount > 40000:
        return 500.0
    elif amount <= 1000:
        return 50.0
    elif amount <= 20000:
        return 100.0
    else:
        return 200.0 + amount * 0.01
