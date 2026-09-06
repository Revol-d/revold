# ADR-0018: Canal de notificação por e-mail (SMTP)

**Status:** Aceito

## Contexto

`NotificationChannel` (`core-notification/ports.py`) já existia desde o início do projeto, mas só tinha um adapter: `LoggingNotificationChannel`, que só loga — nenhum canal real de aviso para a Nick existia. `NOTIFICATION_PROVIDER=smtp` já aparecia estubado em `adapters_external/notification/factory.py` desde a Onda 1 (ADR-0013), levantando `NotImplementedError` de propósito até o adapter de verdade ser escrito.

Diferente de Azure AD, Google ou WhatsApp Business API (que exigem negociação corporativa ou aprovação de terceiros para conseguir uma credencial), uma conta SMTP é trivial de obter — SendGrid, Amazon SES, ou até um Gmail com senha de app. Isso coloca este leaf na Categoria B do `planejamento-leafs-e-adaptadores.md`: sandbox real hoje, credencial de produção quando a Nick decidir qual provedor usar.

## Decisão

**Nenhuma porta nova** — `NotificationChannel.send(notification) -> None` já existia e não precisou mudar; só um segundo adapter:

- **`SmtpNotificationChannel`** (`adapters/external`): monta um `email.message.EmailMessage` (assunto `[revold] {event_type}`, corpo = `notification.message`) e entrega via `aiosmtplib` (cliente SMTP assíncrono).
- Testado de ponta a ponta contra o **aiosmtpd** — um servidor SMTP real, em memória, puro Python. Diferente de Azurite (Wave 2) ou de um `service` Docker do CI, aiosmtpd não precisa de Docker nem de porta fixa: sobe e derruba dentro do próprio processo de teste, numa porta livre escolhida na hora. Prova o protocolo SMTP de verdade (EHLO, MAIL FROM, RCPT TO, DATA) sem mockar a chamada de rede.
- Seleção via `NOTIFICATION_PROVIDER=smtp` (já existente desde ADR-0013), com `SMTP_HOST`/`SMTP_PORT`/`SMTP_FROM_ADDRESS`/`NICK_NOTIFICATION_EMAIL` obrigatórios (levanta `NotImplementedError` com mensagem explicando o que falta, se incompleto) e `SMTP_USERNAME`/`SMTP_PASSWORD`/`SMTP_USE_TLS` opcionais.

## Testes

- `adapters/external/tests/test_smtp_channel.py` (`@pytest.mark.integration`): entrega real via aiosmtpd — remetente/destinatário/assunto/corpo corretos, múltiplas notificações entregues em sequência.
- `adapters/external/tests/test_notification_factory.py`: seleção de provider (`logging` default, `smtp` configurado corretamente, `smtp` incompleto levanta erro, provider desconhecido levanta erro) — nenhum destes precisava de teste antes; a fábrica nunca tinha sido exercitada.

## Consequências

- `LoggingNotificationChannel` continua sendo o default — nada muda para quem não configurar `NOTIFICATION_PROVIDER=smtp`.
- Quando a Nick (ou qualquer projeto futuro do framework) decidir qual provedor SMTP usar, ativar é só configurar as variáveis de ambiente — nenhum código muda.
- Fecha o último item pendente do backlog de canais de notificação (`planejamento-leafs-e-adaptadores.md`, item 3).
