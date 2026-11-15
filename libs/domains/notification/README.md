# `revold_notification`

Avisos operacionais para a loja: novo checkout e estoque baixo.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `smtp`, `whatsapp`

## O que faz

A entidade `Notification` e os casos de uso `NotifyNewCheckout` e `NotifyLowStock`, a porta `NotificationChannel` e os adapters em `adapters/`: log, e-mail SMTP (ADR-0018), WhatsApp Business (ADR-0025) e a factory `build_notification_channel`.

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não conhece carrinho nem estoque.** Recebe só texto e primitivos, montados por quem dispara o aviso.
- **Não fala com SMTP nem com a Meta diretamente.** Usa os clientes de `libs/integrations/smtp` e `libs/integrations/whatsapp`.

## Testes

```powershell
uv run pytest libs/domains/notification/tests -q
```
