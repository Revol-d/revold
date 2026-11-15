# `api_gateway`

API HTTP da loja (composition root): rotas FastAPI sobre os domínios e o produto.

- **Tipo:** app · **Runtime:** fastapi-api · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `ai-assistant`, `cart`, `catalog`, `communication`, `ecommerce`, `identity`, `inventory`, `messaging`, `notification`, `orders`, `payments`, `platform`, `postgres`, `prometheus`, `redis`, `store-settings`

## O que faz

Monta os adapters reais (`dependencies.py`), expõe as rotas de cada contexto (`routers/`), a autenticação por sessão e por API key (`security.py`), `/metrics` e `/health`. `settings.py` é o único módulo que lê o ambiente. `python -m api_gateway.seed` roda o seed semântico.

## O que NÃO faz

- **Não guarda regra de negócio.** Regra de um contexto mora no domínio; regra que cruza contextos, no produto.
- **Não é importado por outro app.** O que dois apps precisam mora no produto ou numa lib.

## Testes

```powershell
uv run pytest apps/ecommerce/api-gateway/tests -q
```
