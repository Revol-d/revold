"""`dev affected` sobre o manifesto REAL: arquivos -> unidades -> consumidores."""

from __future__ import annotations

from pathlib import Path

import pytest
from revold_tooling.affected import compute_affected
from revold_tooling.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(ROOT)


def test_docs_only_change_affects_nothing(manifest):
    result = compute_affected(manifest, ["docs/branch-strategy.md", "README.md", "CONTRIBUTING.md"])
    assert result.units == ()
    assert not result.any


def test_integration_change_affects_the_domains_and_apps_that_use_it(manifest):
    result = compute_affected(manifest, ["libs/integrations/smtp/src/revold_smtp/mailer.py"])
    # smtp -> notification -> ecommerce -> os apps que usam o produto.
    assert {"smtp", "notification", "ecommerce", "api-gateway", "event-worker"} <= set(result.units)
    assert "cart" not in result.units, "cart nao depende de smtp"
    assert "storefront" not in result.units, "site nao depende de unidade Python"


def test_domain_change_does_not_affect_its_dependencies(manifest):
    result = compute_affected(manifest, ["libs/domains/cart/src/revold_cart/domain/__init__.py"])
    assert "cart" in result.units and "api-gateway" in result.units
    assert "platform" not in result.units
    assert "catalog" not in result.units, "dominio nao depende de dominio"


def test_web_lib_change_affects_only_the_sites_that_use_it(manifest):
    result = compute_affected(manifest, ["libs/web/ui/src/index.ts"])
    assert set(result.units) == {"ui", "storefront"}


def test_global_file_affects_everything(manifest):
    result = compute_affected(manifest, ["uv.lock"])
    assert result.global_change
    assert set(result.units) == {u.id for u in manifest.units}


def test_migration_belongs_to_the_product(manifest):
    result = compute_affected(manifest, ["products/ecommerce/migrations/versions/0009_example.py"])
    assert "ecommerce" in result.units
    assert "cart" not in result.units


def test_pnpm_lock_affects_the_web_units(manifest):
    result = compute_affected(manifest, ["pnpm-lock.yaml"])
    # O painel nao depende da lib web, mas instala pelo mesmo lock: tem que entrar tambem.
    assert set(result.units) == {"ui", "storefront", "admin-dashboard"}


def test_windows_separators_are_accepted(manifest):
    result = compute_affected(manifest, ["libs\\domains\\orders\\README.md"])
    assert "orders" in result.units
