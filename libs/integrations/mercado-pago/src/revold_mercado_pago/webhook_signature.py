"""Assinatura do webhook do Mercado Pago (webhooks v2). Função pura: não faz chamada de rede."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping


def is_valid_webhook_signature(
    *, secret: str, headers: Mapping[str, str], query_params: Mapping[str, str]
) -> bool:
    """Confere o `x-signature` contra o segredo do webhook configurado na conta.

    O cabeçalho `x-signature` carrega `ts=<epoch>,v1=<hmac-hex>`; o manifesto assinado é
    `id:<data.id>;request-id:<x-request-id>;ts:<ts>;` (HMAC-SHA256). O corpo da requisição não
    entra na assinatura, só esses três campos.
    """
    signature_header = headers.get("x-signature", "")
    request_id = headers.get("x-request-id", "")
    data_id = query_params.get("data.id", "")
    if not signature_header or not request_id or not data_id:
        return False

    parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    ts = parts.get("ts")
    received_v1 = parts.get("v1")
    if not ts or not received_v1:
        return False

    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    expected = hmac.new(
        secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, received_v1)
