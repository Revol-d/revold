"""Cliente HTTP da API de pagamentos do Mercado Pago (ADR-0024).

Pix é uma cobrança direta: `POST /v1/payments` com `payment_method_id="pix"` devolve o id do
pagamento imediatamente, junto com QR code e "copia e cola". O mesmo id volta no webhook, então
a reconciliação é direta.

Validado em sandbox via `respx`, com os formatos de request/response documentados publicamente,
não com uma conta de sandbox real: não existe emulador oficial do Mercado Pago.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

_API_BASE = "https://api.mercadopago.com"
_TIMEOUT_SECONDS = 15.0


class MercadoPagoClient:
    """Chamadas à API de pagamentos. Devolve o JSON da resposta, sem interpretar."""

    def __init__(self, *, access_token: str) -> None:
        self._access_token = access_token

    def _write_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": uuid.uuid4().hex,
        }

    async def create_pix_payment(
        self,
        *,
        amount: float,
        description: str,
        payer_email: str,
        external_reference: str,
    ) -> dict[str, Any]:
        """Cria um pagamento Pix e devolve a resposta da API (o `id` e o `point_of_interaction`)."""
        body = {
            "transaction_amount": amount,
            "description": description,
            "payment_method_id": "pix",
            "payer": {"email": payer_email},
            "external_reference": external_reference,
        }
        async with httpx.AsyncClient(base_url=_API_BASE, timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post("/v1/payments", json=body, headers=self._write_headers())
            response.raise_for_status()
            return response.json()

    async def get_payment(self, payment_id: str) -> dict[str, Any]:
        """Consulta um pagamento pelo id e devolve a resposta da API (o campo `status`)."""
        async with httpx.AsyncClient(base_url=_API_BASE, timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"/v1/payments/{payment_id}",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            response.raise_for_status()
            return response.json()
