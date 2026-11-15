"""Cliente do WhatsApp: a Cloud API da Meta e o link de clique-para-conversar.

- `cloud_api.WhatsAppCloudClient`: envia mensagem de texto ou de template pela WhatsApp Business
  Platform (ADR-0025). Faz chamada de rede.
- `click_to_chat.build_click_to_chat_url`: monta o link `wa.me` (ADR-0005). Não faz I/O, por
  isso está em `pure_modules` do `unit.yaml`.

Não sabe o que é notificação nem carrinho. O texto da mensagem é montado pela camada `adapters/`
do domínio que a envia.
"""

__all__ = ["click_to_chat", "cloud_api"]
