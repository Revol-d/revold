"""Adapter real de core_events.ports.WebhookSender — entrega HTTP com
retry/backoff exponencial (ADR-0016). Zero credencial: qualquer endpoint
HTTP de um parceiro/integração serve, inclusive um receptor local — testado
de ponta a ponta contra um app FastAPI de teste via ASGITransport (ver
adapters/messaging/tests/test_http_webhook_sender.py), sem precisar de
nenhum servidor real escutando numa porta.
"""
from __future__ import annotations

import asyncio

import httpx

from core_events.domain import DomainEvent


class HttpWebhookSender:
    provider_name = "http"

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
        timeout_seconds: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # `transport` só existe para teste (ASGITransport contra um app de
        # verdade em memória) — em produção nunca é passado, e o httpx usa
        # a rede de verdade.
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def send(self, url: str, event: DomainEvent) -> bool:
        payload = {"name": event.name, "payload": event.payload}
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds, transport=self._transport
        ) as client:
            for attempt in range(1, self._max_attempts + 1):
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code < 300:
                        return True
                except httpx.HTTPError:
                    pass
                if attempt < self._max_attempts:
                    # backoff exponencial: 0.5s, 1s, 2s... (com
                    # backoff_base_seconds=0.5) — não bloqueia o worker
                    # inteiro, só esta tarefa (await, não sleep síncrono).
                    await asyncio.sleep(self._backoff_base_seconds * (2 ** (attempt - 1)))
        return False
