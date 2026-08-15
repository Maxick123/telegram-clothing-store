def test_yookassa_amount_uses_two_decimal_rubles() -> None:
    from app.modules.payments.yookassa_provider import kopecks_to_rub

    assert kopecks_to_rub(599000) == "5990.00"
    assert kopecks_to_rub(1) == "0.01"
