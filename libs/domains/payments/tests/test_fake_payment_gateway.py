from __future__ import annotations

from decimal import Decimal

from revold_payments.adapters.gateways.fake_gateway import FakePaymentGateway
from revold_payments.domain import ChargeStatus, Money, PaymentMethod


async def test_create_charge_pix_devolve_qr_code() -> None:
    gateway = FakePaymentGateway()
    charge = await gateway.create_charge(
        order_id="o1", amount=Money(Decimal("50")), method=PaymentMethod.PIX
    )
    assert charge.pix_qr_code is not None
    assert charge.pix_copy_paste is not None
    assert charge.checkout_url is None


async def test_create_charge_cartao_devolve_checkout_url() -> None:
    gateway = FakePaymentGateway()
    charge = await gateway.create_charge(
        order_id="o1", amount=Money(Decimal("50")), method=PaymentMethod.CREDIT_CARD
    )
    assert charge.checkout_url is not None
    assert charge.pix_qr_code is None


async def test_get_charge_status_aprova_na_primeira_consulta_por_padrao() -> None:
    gateway = FakePaymentGateway()
    charge = await gateway.create_charge(
        order_id="o1", amount=Money(Decimal("50")), method=PaymentMethod.PIX
    )
    status = await gateway.get_charge_status(charge.provider_charge_id)
    assert status == ChargeStatus.PAID


async def test_get_charge_status_respeita_approve_after_polls() -> None:
    gateway = FakePaymentGateway(approve_after_polls=2)
    charge = await gateway.create_charge(
        order_id="o1", amount=Money(Decimal("50")), method=PaymentMethod.PIX
    )
    assert await gateway.get_charge_status(charge.provider_charge_id) == ChargeStatus.PENDING
    assert await gateway.get_charge_status(charge.provider_charge_id) == ChargeStatus.PENDING
    assert await gateway.get_charge_status(charge.provider_charge_id) == ChargeStatus.PAID


def test_verify_webhook_signature_exige_header_nao_vazio() -> None:
    gateway = FakePaymentGateway()
    assert gateway.verify_webhook_signature(headers={"x-signature": "qualquer"}, query_params={}, body=b"") is True
    assert gateway.verify_webhook_signature(headers={}, query_params={}, body=b"") is False
