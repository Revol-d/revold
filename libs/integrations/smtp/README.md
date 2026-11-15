# `revold_smtp`

Cliente SMTP: entrega uma mensagem de e-mail pronta a um servidor SMTP.

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

`SmtpMailer(host, port, username, password, use_tls).send(message)`: entrega uma `EmailMessage`.

## O que NÃO faz

- **Não monta a mensagem.** Assunto, remetente e corpo são de quem envia (hoje, o domínio `notification`, ADR-0018).
- **Não lê `SMTP_*`.** A configuração chega por parâmetro.

## Testes

```powershell
uv run pytest libs/integrations/smtp/tests -q
```
