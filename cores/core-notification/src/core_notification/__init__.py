"""core-notification: alertas para a Nick.

Avisa a Nick sobre eventos operacionais (novo pedido em checkout, estoque
baixo, etc.) através de um canal de notificação (core_notification.ports.
NotificationChannel). Não importa core_cart, core_inventory nem
core_communication (ADR-0002) — quem dispara uma notificação (o
api-gateway, orquestrando) monta a mensagem a partir dos dados do core de
origem e passa só texto/primitivos para cá.

A implementação de canal usada hoje (adapters_external/notification) é um
stand-in que só registra a notificação — não existe ainda WhatsApp
Business API nem serviço de e-mail configurado. Trocar por um canal real é
só trocar o que a factory do api-gateway devolve.
"""
