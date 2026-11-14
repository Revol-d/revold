from __future__ import annotations

from decimal import Decimal

import pytest

from core_payments.domain import ChargeNotFound, ChargeStatus, Money, PaymentMethod
from core_payments.use_cases import ConfirmChargeFromWebhook, CreateCharge, GetCharge, GetChargeByOrder


async def test_create_charge_chama_gateway_e_persiste(fake_gateway, fake_repository) -> None:
    charge = await CreateCharge(fake_gateway, fake_repository).execute(
        order_id="o1", amount=Money(Decimal("100")), method=PaymentMethod.PIX
    )
    assert charge.charge_id
    assert charge.pix_qr_code is not None
    assert fake_gateway.created == [("o1", Money(Decimal("100")), PaymentMethod.PIX)]

    persisted = await fake_repository.get(charge.charge_id)
    assert persisted == charge


async def test_create_charge_cartao_devolve_checkout_url(fake_gateway, fake_repository) -> None:
    charge = await CreateCharge(fake_gateway, fake_repository).execute(
        order_id="o1", amount=Money(Decimal("100")), method=PaymentMethod.CREDIT_CARD
    )
    assert charge.checkout_url == "https://fake.test/checkout"
    assert charge.pix_qr_code is None


async def test_create_charge_reaproveita_cobranca_pendente_do_mesmo_pedido(
    fake_gateway, fake_repository
) -> None:
    first = await CreateCharge(fake_gateway, fake_repository).execute(
        order_id="o1", amount=Money(Decimal("100")), method=PaymentMethod.PIX
    )
    second = await CreateCharge(fake_gateway, fake_repository).execute(
        order_id="o1", amount=Money(Decimal("100")), method=PaymentMethod.PIX
    )
    assert first.charge_id == second.charge_id
    assert len(fake_gateway.created) == 1  # não abriu uma segunda cobrança no gateway


async def test_get_charge_inexistente_levanta_not_found(fake_repository) -> None:
    with pytest.raises(ChargeNotFound):
        await GetCharge(fake_repository).execute("nao-existe")


async def test_get_charge_by_order(fake_gateway, fake_repository) -> None:
    created = await CreateCharge(fake_gateway, fake_repository).execute(
        order_id="o1", amount=Money(Decimal("50")), method=PaymentMethod.PIX
    )
    found = await GetChargeByOrder(fake_repository).execute("o1")
    assert found.charge_id == created.charge_id


async def test_confirm_charge_from_webhook_marca_pago_quando_gateway_confirma(
    fake_gateway, fake_repository
) -> None:
    charge = await CreateCharge(fake_gateway, fake_repository).execute(
        order_id="o1", amount=Money(Decimal("50")), method=PaymentMethod.PIX
    )
    fake_gateway.set_next_status(charge.provider_charge_id, ChargeStatus.PAID)

    confirmed = await ConfirmChargeFromWebhook(fake_gateway, fake_repository).execute(
        charge.provider_charge_id
    )
    assert confirmed.status == ChargeStatus.PAID

    persisted = await fake_repository.get(charge.charge_id)
    assert persisted is not None
    assert persisted.status == ChargeStatus.PAID


async def test_confirm_charge_from_webhook_ignora_status_pending_do_gateway(
    fake_gateway, fake_repository
) -> None:
    charge = await CreateCharge(fake_gateway, fake_repository).execute(
        order_id="o1", amount=Money(Decimal("50")), method=PaymentMethod.PIX
    )
    confirmed = await ConfirmChargeFromWebhook(fake_gateway, fake_repository).execute(
        charge.provider_charge_id
    )
    assert confirmed.status == ChargeStatus.PENDING


async def test_confirm_charge_from_webhook_e_idempotente(fake_gateway, fake_repository) -> None:
    charge = await CreateCharge(fake_gateway, fake_repository).execute(
        order_id="o1", amount=Money(Decimal("50")), method=PaymentMethod.PIX
    )
    fake_gateway.set_next_status(charge.provider_charge_id, ChargeStatus.PAID)
    await ConfirmChargeFromWebhook(fake_gateway, fake_repository).execute(charge.provider_charge_id)

    # gateway agora "mudaria" pra outro status, mas a cobrança já não é
    # mais PENDING localmente — webhook duplicado não deve reprocessar.
    fake_gateway.set_next_status(charge.provider_charge_id, ChargeStatus.FAILED)
    result = await ConfirmChargeFromWebhook(fake_gateway, fake_repository).execute(
        charge.provider_charge_id
    )
    assert result.status == ChargeStatus.PAID


async def test_confirm_charge_from_webhook_id_desconhecido_levanta_not_found(
    fake_gateway, fake_repository
) -> None:
    with pytest.raises(ChargeNotFound):
        await ConfirmChargeFromWebhook(fake_gateway, fake_repository).execute("nao-existe")
