# `revold_platform`

Infraestrutura de todo app: configuração, eventos de domínio e observabilidade.

- **Tipo:** platform · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

| Subpacote | O que tem |
|---|---|
| `configuration` | `env_str`, `env_bool`, `env_int`, `env_list`, `env_required` e `env_snapshot`: o parser de ambiente único. É o único lugar de `libs/` que toca `os.environ` |
| `events` | `DomainEvent`, as portas `EventPublisher` e `WebhookSender` (ADR-0013, ADR-0016) e os dois adapters que não falam com sistema nenhum: `InMemoryEventPublisher` e `LoggingWebhookSender` |
| `observability` | a porta `MetricsPublisher` (ADR-0017) |

## O que NÃO faz

- **Não decide quais variáveis existem.** Isso é do `settings.py` de cada app.
- **Não fala com fila, HTTP nem Prometheus.** Isso é de `libs/integrations/messaging` e `libs/integrations/prometheus`.
- **Não guarda regra de negócio.** "É genérico, vai para a platform" é como uma lib vira depósito: só entra aqui o que todo app usa.

## Testes

```powershell
uv run pytest libs/platform/tests -q
```
