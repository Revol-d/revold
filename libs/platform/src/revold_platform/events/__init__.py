"""Eventos de domínio: a definição de evento e as portas de publicação e de entrega.

Centraliza o formato do evento para todo o monorepo. Em vez de cada domínio inventar o seu (o
que levaria a duplicação e a consumo divergente), quem precisa publicar algo assíncrono importa
só `revold_platform.events.domain.DomainEvent` e `revold_platform.events.ports.EventPublisher`
(ADR-0013).

Os adapters que falam com um sistema externo (Celery, HTTP) moram em `libs/integrations/messaging`.
Os dois que não falam com ninguém ficam aqui: `in_memory_publisher` e `logging_webhook_sender`,
usados em teste e no modo local dos apps.
"""
