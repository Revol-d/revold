# `revold_whatsapp`

Cliente do WhatsApp: a Cloud API da Meta e o link de clique-para-conversar.

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

- `cloud_api.WhatsAppCloudClient`: envia mensagem de texto ou de template pela WhatsApp Business Platform (ADR-0025);
- `click_to_chat.build_click_to_chat_url(number, message)`: monta o link `wa.me` (ADR-0005). Sem I/O, por isso está em `pure_modules`.

## O que NÃO faz

- **Não decide o texto.** O que dizer é da camada `adapters/` do domínio que envia (`notification`, `communication`).
- **Não contorna a janela de 24h da Meta.** Fora dela só template aprovado passa; a escolha entre texto e template é de quem chama.

## Testes

```powershell
uv run pytest libs/integrations/whatsapp/tests -q
```
