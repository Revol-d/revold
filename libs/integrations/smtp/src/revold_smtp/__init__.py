"""Cliente SMTP: entrega uma mensagem de e-mail pronta a um servidor SMTP.

Não sabe o que é notificação, pedido nem loja. Quem monta a mensagem a partir de um evento de
negócio é a camada `adapters/` do domínio que a envia (hoje, `notification`, ADR-0018).
"""

from revold_smtp.mailer import SmtpMailer

__all__ = ["SmtpMailer"]
