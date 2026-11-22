# `catalog_indexer`

Worker Celery que reindexa o catálogo inteiro para o assistente (composition root).

- **Tipo:** app · **Runtime:** celery-worker · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `ai-assistant`, `catalog`, `ecommerce`, `platform`, `azure-sql`

## O que faz

Registra a tarefa `catalog_indexer.reindex_catalog`, monta os adapters reais e chama `revold_ecommerce.application.catalog_indexing.reindex_all_products`. `settings.py` é o único módulo que lê o ambiente.

## O que NÃO faz

- **Não guarda a regra da reindexação.** Ela mora no produto, e por isso o api-gateway e o event-worker a usam sem importar este app.
- **Não agenda a si mesmo.** O agendamento periódico (Celery beat) ainda não existe.

## Testes

```powershell
uv run pytest apps/ecommerce/catalog-indexer/tests -q
```
