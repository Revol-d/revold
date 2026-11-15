"""Domínio de comunicação: a passagem do checkout para um canal de conversa.

Porta CheckoutHandoff (ver ADR-0005). A implementação de hoje é
revold_communication.adapters.whatsapp_clicktochat (link wa.me, sem
WhatsApp Business API). O aviso assíncrono à loja é de outro domínio,
`notification`.
"""
