from __future__ import annotations

import pytest

from revold_payments.domain import Charge, ChargeStatus, Money, PaymentMethod


class FakeChargeRepository:
    def __init__(self) -> None:
        self._charges: dict[str, Charge] = {}

    async def get(self, charge_id: str) -> Charge | None:
        return self._charges.get(charge_id)

    async def get_by_order(self, order_id: str) -> Charge | None:
        return next((c for c in self._charges.values() if c.order_id == order_id), None)

    async def get_by_provider_charge_id(self, provider_charge_id: str) -> Charge | None:
        return next(
            (c for c in self._charges.values() if c.provider_charge_id == provider_charge_id), None
        )

    async def save(self, charge: Charge) -> None:
        self._charges[charge.charge_id] = charge


class FakePaymentGatewayForTests:
    """Não é o adapter de produção (ver revold_payments.adapters.gateways.fake_gateway)
    — é um dublê de teste ainda mais simples, controlado à mão pelo teste."""

    provider_name = "fake-test"

    def __init__(self) -> None:
        self.created: list[tuple[str, Money, PaymentMethod]] = []
        self._next_status: dict[str, ChargeStatus] = {}

    async def create_charge(self, *, order_id: str, amount: Money, method: PaymentMethod) -> Charge:
        self.created.append((order_id, amount, method))
        provider_charge_id = f"prov-{len(self.created)}"
        return Charge(
            charge_id="",
            order_id=order_id,
            provider=self.provider_name,
            provider_charge_id=provider_charge_id,
            method=method,
            amount=amount,
            pix_qr_code="00020126...fake" if method == PaymentMethod.PIX else None,
            pix_copy_paste="00020126fake-copy-paste" if method == PaymentMethod.PIX else None,
            checkout_url="https://fake.test/checkout" if method == PaymentMethod.CREDIT_CARD else None,
        )

    def set_next_status(self, provider_charge_id: str, status: ChargeStatus) -> None:
        self._next_status[provider_charge_id] = status

    async def get_charge_status(self, provider_charge_id: str) -> ChargeStatus:
        return self._next_status.get(provider_charge_id, ChargeStatus.PENDING)

    def verify_webhook_signature(self, *, headers, query_params, body: bytes) -> bool:
        return headers.get("x-signature") == "valid"


@pytest.fixture
def fake_repository() -> FakeChargeRepository:
    return FakeChargeRepository()


@pytest.fixture
def fake_gateway() -> FakePaymentGatewayForTests:
    return FakePaymentGatewayForTests()
