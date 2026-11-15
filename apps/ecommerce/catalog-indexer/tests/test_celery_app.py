"""Smoke do composition root: o app sobe e registra a tarefa com o nome que quem agenda usa.

A regra da reindexação mora no produto e tem a suíte dela
(products/ecommerce/tests/test_catalog_indexing.py). Aqui só se confere a montagem, sem broker
nem banco: criar o app Celery não abre conexão nenhuma.
"""

from __future__ import annotations

from catalog_indexer import celery_app, settings


def test_reindex_task_is_registered_under_its_public_name() -> None:
    assert "catalog_indexer.reindex_catalog" in celery_app.celery_app.tasks


def test_broker_comes_from_settings(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://broker.example:6379/3")
    assert settings.redis_url() == "redis://broker.example:6379/3"


def test_llm_settings_default_to_the_dev_provider(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert settings.llm_settings().provider == "dev"
