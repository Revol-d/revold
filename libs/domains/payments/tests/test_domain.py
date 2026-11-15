from __future__ import annotations

from decimal import Decimal

import pytest

from revold_payments.domain import Charge, ChargeStatus, InvalidChargeTransition, Money, PaymentMethod


def _charge(**kwargs) -> Charge:
    defaults = dict(
        charge_id="c1",
        order_id="o1",
        provider="fake",
        provider_charge_id="prov-1",
        method=PaymentMethod.PIX,
        amount=Money(Decimal("100")),
    )
    defaults.update(kwargs)
    return Charge(**defaults)


def test_money_exige_valor_positivo() -> None:
    with pytest.raises(ValueError):
        Money(Decimal("0"))
    with pytest.raises(ValueError):
        Money(Decimal("-10"))


def test_charge_nasce_pending() -> None:
    assert _charge().status == ChargeStatus.PENDING


def test_mark_paid_a_partir_de_pending() -> None:
    charge = _charge()
    charge.mark_paid()
    assert charge.status == ChargeStatus.PAID


def test_mark_paid_duas_vezes_e_invalido() -> None:
    charge = _charge()
    charge.mark_paid()
    with pytest.raises(InvalidChargeTransition):
        charge.mark_paid()


def test_mark_failed_a_partir_de_pending() -> None:
    charge = _charge()
    charge.mark_failed()
    assert charge.status == ChargeStatus.FAILED


def test_mark_expired_a_partir_de_pending() -> None:
    charge = _charge()
    charge.mark_expired()
    assert charge.status == ChargeStatus.EXPIRED


def test_mark_refunded_exige_pago() -> None:
    charge = _charge()
    with pytest.raises(InvalidChargeTransition):
        charge.mark_refunded()
    charge.mark_paid()
    charge.mark_refunded()
    assert charge.status == ChargeStatus.REFUNDED
