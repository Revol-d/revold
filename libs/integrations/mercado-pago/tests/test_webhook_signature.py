"""A assinatura do webhook: função pura, sem rede."""

from __future__ import annotations

import hashlib
import hmac

from revold_mercado_pago.webhook_signature import is_valid_webhook_signature

_SECRET = "segredo-de-teste-nao-e-real"
_QUERY = {"data.id": "123"}


def _signed_headers(
    *, data_id: str, request_id: str, ts: str, secret: str = _SECRET
) -> dict[str, str]:
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    return {"x-signature": f"ts={ts},v1={v1}", "x-request-id": request_id}


def test_valid_signature_is_accepted() -> None:
    headers = _signed_headers(data_id="123", request_id="req-1", ts="1700000000")

    assert is_valid_webhook_signature(secret=_SECRET, headers=headers, query_params=_QUERY)


def test_signature_made_with_another_secret_is_refused() -> None:
    headers = _signed_headers(data_id="123", request_id="req-1", ts="1700000000", secret="outro")

    assert not is_valid_webhook_signature(secret=_SECRET, headers=headers, query_params=_QUERY)


def test_signature_for_another_payment_is_refused() -> None:
    headers = _signed_headers(data_id="123", request_id="req-1", ts="1700000000")

    assert not is_valid_webhook_signature(
        secret=_SECRET, headers=headers, query_params={"data.id": "999"}
    )


def test_missing_pieces_are_refused() -> None:
    headers = _signed_headers(data_id="123", request_id="req-1", ts="1700000000")
    malformed = {**headers, "x-signature": "sem-formato"}

    assert not is_valid_webhook_signature(secret=_SECRET, headers={}, query_params=_QUERY)
    assert not is_valid_webhook_signature(secret=_SECRET, headers=headers, query_params={})
    assert not is_valid_webhook_signature(secret=_SECRET, headers=malformed, query_params=_QUERY)
