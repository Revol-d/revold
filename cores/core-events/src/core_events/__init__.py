"""core-events: bounded context central de eventos de domínio.

Centraliza a definição de evento e a porta de publicação para todo o
monorepo — em vez de cada core inventar seu próprio formato de evento (o
que levaria a duplicação e a problemas de deduplicação/consumo divergente
entre consumidores), qualquer core que precise publicar algo assíncrono
(catálogo, checkout, estoque, o que vier depois) importa só
`core_events.domain.DomainEvent` e `core_events.ports.EventPublisher`.

Nunca importa nada de outro core (ADR-0002) — só primitivos.
"""
