"""catalog-indexer: reindexação do catálogo para o índice vetorial do
assistente de IA (RAG, ver ADR-0011). Orquestração cross-core (lê
core-catalog, escreve em core-ai-assistant) — por isso vive em workers/,
não dentro de nenhum dos dois cores (ADR-0002)."""
