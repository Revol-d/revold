"""catalog-indexer: o worker que reindexa o catálogo inteiro para o índice
vetorial do assistente de IA (RAG, ver ADR-0011).

Este app só monta as dependências e registra a tarefa Celery. A regra da
reindexação cruza dois domínios (lê o catálogo, escreve no assistente) e
por isso mora no produto: revold_ecommerce.application.catalog_indexing
(ADR-0002, ADR-0027)."""
