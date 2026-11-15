"""`dev new` e os gerados.

O risco que estes testes cobrem: **o tool mentir que deu certo**. Nome invalido derruba antes de
escrever, e falha no meio desfaz tudo.
"""

from __future__ import annotations

import pytest
from revold_tooling.generate import render_codeowners, render_importlinter, stale_generated
from revold_tooling.manifest import load_manifest
from revold_tooling.scaffold import NewUnit, create_unit


@pytest.mark.parametrize(
    "bad_id", ["Meu-Modulo", "meu_modulo", "1abc", "class", "abc-import", "abc-"]
)
def test_invalid_id_fails_before_writing(repo, bad_id):
    before = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*"))
    with pytest.raises(ValueError):
        create_unit(repo, NewUnit(kind="capability", id=bad_id))
    assert sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*")) == before


def test_domain_is_created_with_layers_and_valid_manifest(repo):
    create_unit(repo, NewUnit(kind="integration", id="gateway", depends_on=("platform",)))
    target = create_unit(
        repo, NewUnit(kind="domain", id="billing", depends_on=("platform", "gateway"))
    ).target

    package = target / "src" / "revold_billing"
    for layer in ("domain", "application", "ports", "adapters", "adapters/memory"):
        assert (package / layer / "__init__.py").is_file(), layer
    assert not (package / "testing").exists()
    pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dependencies = ["revold-platform", "revold-gateway"]' in pyproject
    assert 'packages = ["src/revold_billing"]' in pyproject
    assert (target / "tests" / "test_revold_billing_public_api.py").is_file()

    manifest = load_manifest(repo)
    assert manifest.by_id["billing"].depends_on == ("platform", "gateway")
    assert "revold-billing = { workspace = true }" in (repo / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert stale_generated(manifest) == []


def test_product_is_created_with_its_four_layers(repo):
    target = create_unit(
        repo, NewUnit(kind="product", id="loja", product="loja", depends_on=("platform",))
    ).target

    package = target / "src" / "revold_loja"
    for layer in ("domain", "application", "ports", "adapters"):
        assert (package / layer / "__init__.py").is_file(), layer
    assert load_manifest(repo).by_id["loja"].product == "loja"


def test_unknown_dependency_creates_nothing(repo):
    with pytest.raises(ValueError, match="nao existem"):
        create_unit(repo, NewUnit(kind="capability", id="x", depends_on=("fantasma",)))
    assert not (repo / "libs" / "capabilities" / "x").exists()


def test_rule_violation_rolls_back_folder_and_root_pyproject(repo):
    original = (repo / "pyproject.toml").read_text(encoding="utf-8")
    create_unit(repo, NewUnit(kind="domain", id="dom", depends_on=("platform",)))
    after_domain = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert after_domain != original

    with pytest.raises(Exception, match="D1"):
        create_unit(repo, NewUnit(kind="integration", id="bad", depends_on=("dom",)))
    assert not (repo / "libs" / "integrations" / "bad").exists()
    assert (repo / "pyproject.toml").read_text(encoding="utf-8") == after_domain


def test_app_requires_product(repo):
    with pytest.raises(ValueError, match="--product"):
        create_unit(repo, NewUnit(kind="app", id="job"))


def test_generated_files_are_deterministic(repo):
    create_unit(repo, NewUnit(kind="capability", id="templating"))
    manifest = load_manifest(repo)
    assert render_importlinter(manifest) == render_importlinter(load_manifest(repo))
    owners = render_codeowners(manifest)
    assert "/libs/capabilities/templating/unit.yaml" in owners
    assert owners.splitlines()[0].startswith("# Gerado por `uv run dev gen`")


# --------------------------------------------------------------------- modelos de app
@pytest.mark.parametrize("runtime", ["fastapi-api", "celery-worker"])
def test_python_app_joins_workspace_members_and_depends_on_platform(repo, runtime):
    created = create_unit(repo, NewUnit(kind="app", id="loja/meu-app", runtime=runtime))
    assert created.target == repo / "apps" / "loja" / "meu-app"
    assert created.added_dependencies == ("platform",)
    assert '    "apps/loja/meu-app",' in (repo / "pyproject.toml").read_text(encoding="utf-8")
    unit = load_manifest(repo).by_id["meu-app"]
    assert unit.runtime == runtime and unit.product == "loja"
    assert unit.depends_on == ("platform",)
    assert "revold-platform" in unit.pyproject["project"]["dependencies"]


def test_app_without_runtime_gets_the_default_model(repo):
    create_unit(repo, NewUnit(kind="app", id="loja/api"))
    assert load_manifest(repo).by_id["api"].runtime == "fastapi-api"


def test_fastapi_app_has_factory_health_ready_and_dockerfile(repo):
    target = create_unit(repo, NewUnit(kind="app", id="loja/api", runtime="fastapi-api")).target
    main = (target / "src" / "api" / "main.py").read_text(encoding="utf-8")
    assert "def create_app(" in main and '"/health"' in main and '"/ready"' in main
    dockerfile = (target / "Dockerfile").read_text(encoding="utf-8")
    assert "uv sync --frozen --no-default-groups --package api" in dockerfile
    assert (target / "tests" / "test_api_smoke.py").is_file()


def test_celery_worker_app_reads_environment_only_in_settings(repo):
    target = create_unit(repo, NewUnit(kind="app", id="loja/fila", runtime="celery-worker")).target
    package = target / "src" / "fila"
    assert "revold_platform.configuration" in (package / "settings.py").read_text(encoding="utf-8")
    assert "os.environ" not in (package / "celery_app.py").read_text(encoding="utf-8")
    assert '@celery_app.task(name="fila.ping")' in (package / "celery_app.py").read_text(
        encoding="utf-8"
    )


def test_dry_run_writes_nothing(repo):
    before = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*"))
    created = create_unit(
        repo, NewUnit(kind="app", id="loja/api", runtime="fastapi-api"), dry_run=True
    )
    assert "Dockerfile" in created.files and "unit.yaml" in created.files
    assert sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*")) == before


@pytest.mark.parametrize(
    ("request_", "message"),
    [
        (NewUnit(kind="app", id="loja/api", product="outro"), "contradiz"),
        (NewUnit(kind="capability", id="x", runtime="fastapi-api"), "--runtime so vale"),
        (NewUnit(kind="app", id="loja/site", runtime="next-web"), "nao tem modelo"),
    ],
)
def test_bad_app_requests_fail_before_writing(repo, request_, message):
    with pytest.raises(ValueError, match=message):
        create_unit(repo, request_)
    assert not (repo / "apps").exists()
