"""`notification`: alertas para a Nick.

Avisa a Nick sobre eventos operacionais (novo pedido em checkout, estoque
baixo, etc.) através de um canal de notificação (revold_notification.ports.
NotificationChannel). Não importa revold_cart, revold_inventory nem
revold_communication (ADR-0002) — quem dispara uma notificação (o
api-gateway, orquestrando) monta a mensagem a partir dos dados do core de
origem e passa só texto/primitivos para cá.

Os canais moram em revold_notification.adapters: o de log (o padrão, que só
registra a notificação), o de e-mail SMTP (ADR-0018) e o de WhatsApp
Business (ADR-0025). A escolha é da factory `build_notification_channel`,
com a configuração que o app entrega.
"""
