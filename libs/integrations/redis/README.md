# `revold_redis`

Cliente do Redis assíncrono, compartilhado pelos apps.

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

`make_redis_client(redis_url)`: devolve o cliente `redis.asyncio.Redis` já com `decode_responses`.

## O que NÃO faz

- **Não guarda dado.** Carrinho, sessão e limite de requisições moram em `adapters/redis/` do domínio dono da porta e recebem o cliente pronto.
- **Não lê `REDIS_URL`.** Quem lê é o `settings.py` do app.

## Testes

```powershell
uv run pytest libs/integrations/redis/tests -q
```
