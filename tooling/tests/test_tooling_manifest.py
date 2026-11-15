"""Validacao do manifesto: cada regra tem um caso que a viola e precisa reprovar."""

from __future__ import annotations

from pathlib import Path

import pytest
from revold_tooling.manifest import ManifestError, load_manifest
from tooling_helpers import unit_yaml, write_unit


def _add_source(root: Path, dist: str) -> None:
    pyproject = root / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8") + f"{dist} = {{ workspace = true }}\n",
        encoding="utf-8",
    )


def _problems(root: Path) -> str:
    with pytest.raises(ManifestError) as exc:
        load_manifest(root)
    return "\n".join(exc.value.problems)


def test_valid_manifest_loads(repo):
    manifest = load_manifest(repo)
    assert [u.id for u in manifest.units] == ["platform"]
    assert manifest.by_id["platform"].import_name == "revold_platform"


def test_schema_violation_is_reported(repo):
    (repo / "libs/platform/unit.yaml").write_text(
        unit_yaml("Platform", "platform"), encoding="utf-8"
    )
    assert "id" in _problems(repo)


def test_duplicate_id(repo):
    write_unit(
        repo,
        "libs/capabilities/other",
        unit_yaml("platform", "capability"),
        "revold-other",
        "revold_other",
    )
    _add_source(repo, "revold-other")
    assert "id repetido 'platform'" in _problems(repo)


def test_unknown_dependency(repo):
    write_unit(
        repo,
        "libs/capabilities/x",
        unit_yaml("x", "capability", '["nao-existe"]'),
        "revold-x",
        "revold_x",
    )
    _add_source(repo, "revold-x")
    assert "'nao-existe', que nao existe" in _problems(repo)


def test_d1_rule_integration_cannot_depend_on_domain(repo):
    write_unit(
        repo,
        "libs/domains/d",
        unit_yaml("d", "domain", '["platform"]'),
        "revold-d",
        "revold_d",
        '"revold-platform"',
    )
    write_unit(
        repo,
        "libs/integrations/i",
        unit_yaml("i", "integration", '["d"]'),
        "revold-i",
        "revold_i",
        '"revold-d"',
    )
    _add_source(repo, "revold-d")
    _add_source(repo, "revold-i")
    assert "i (integration) nao pode depender de d (domain)" in _problems(repo)


def test_d1_integration_cannot_depend_on_another_integration(repo):
    # A regra vale inteira: integracao nao depende de integracao. Quem compoe duas e a camada
    # adapters/ de um dominio, ou o app.
    write_unit(
        repo,
        "libs/integrations/a",
        unit_yaml("a", "integration", '["platform"]'),
        "revold-a",
        "revold_a",
        '"revold-platform"',
    )
    write_unit(
        repo,
        "libs/integrations/b",
        unit_yaml("b", "integration", '["a"]'),
        "revold-b",
        "revold_b",
        '"revold-a"',
    )
    for dist in ("revold-a", "revold-b"):
        _add_source(repo, dist)
    assert "b (integration) nao pode depender de a (integration)" in _problems(repo)


def test_cycle_is_reported(repo):
    write_unit(
        repo,
        "libs/capabilities/a",
        unit_yaml("a", "capability", '["b"]'),
        "revold-a",
        "revold_a",
        '"revold-b"',
    )
    write_unit(
        repo,
        "libs/capabilities/b",
        unit_yaml("b", "capability", '["a"]'),
        "revold-b",
        "revold_b",
        '"revold-a"',
    )
    _add_source(repo, "revold-a")
    _add_source(repo, "revold-b")
    assert "ciclo de dependencia" in _problems(repo)


def test_production_cannot_depend_on_prototype(repo):
    write_unit(
        repo,
        "libs/capabilities/p",
        unit_yaml("p", "capability", lifecycle="prototype"),
        "revold-p",
        "revold_p",
    )
    write_unit(
        repo,
        "libs/capabilities/q",
        unit_yaml("q", "capability", '["p"]', lifecycle="production"),
        "revold-q",
        "revold_q",
        '"revold-p"',
    )
    _add_source(repo, "revold-p")
    _add_source(repo, "revold-q")
    assert "q e production e depende de p, que e prototype" in _problems(repo)


def test_pyproject_and_depends_on_must_agree(repo):
    write_unit(
        repo,
        "libs/capabilities/c",
        unit_yaml("c", "capability"),
        "revold-c",
        "revold_c",
        '"revold-platform"',
    )
    _add_source(repo, "revold-c")
    assert "o pyproject.toml pede ['platform'], que faltam no depends_on" in _problems(repo)


def test_unit_must_resolve_from_workspace(repo):
    write_unit(repo, "libs/capabilities/c", unit_yaml("c", "capability"), "revold-c", "revold_c")
    assert "revold-c falta em [tool.uv.sources]" in _problems(repo)


def test_app_requires_runtime(repo):
    write_unit(repo, "apps/loja/job", unit_yaml("job", "app"), "job", "job")
    assert "app precisa de `runtime`" in _problems(repo)


def test_the_real_repository_manifest_is_valid():
    """O manifesto commitado passa; se este teste falhar, o `dev check` do CI tambem falha."""
    root = Path(__file__).resolve().parents[2]
    manifest = load_manifest(root)
    assert "ecommerce" in manifest.by_id


# --------------------------------------------------------------------- pure_modules (D1)
def _integration_with_modules(repo: Path, pure: str) -> None:
    directory = write_unit(
        repo,
        "libs/integrations/svc",
        unit_yaml("svc", "integration", '["platform"]', extra=f"pure_modules: {pure}\n"),
        "revold-svc",
        "revold_svc",
        '"revold-platform"',
    )
    for name in ("models", "client"):
        (directory / "src" / "revold_svc" / name).mkdir()
        (directory / "src" / "revold_svc" / name / "__init__.py").write_text("", encoding="utf-8")
    _add_source(repo, "revold-svc")


def test_pure_modules_lista_os_submodulos_sem_io(repo):
    _integration_with_modules(repo, '["models"]')

    unit = load_manifest(repo).by_id["svc"]

    assert unit.pure_modules == ("models",)
    assert unit.top_level_modules() == ("client", "models")


def test_pure_modules_que_nao_existe_reprova(repo):
    _integration_with_modules(repo, '["nao_existe"]')

    assert "pure_modules cita ['nao_existe']" in _problems(repo)


def test_pure_modules_so_vale_em_integration(repo):
    write_unit(
        repo,
        "libs/capabilities/c",
        unit_yaml("c", "capability", '["platform"]', extra='pure_modules: ["x"]\n'),
        "revold-c",
        "revold_c",
        '"revold-platform"',
    )
    _add_source(repo, "revold-c")

    assert "`pure_modules` so vale em integration" in _problems(repo)


def test_application_pode_importar_o_modulo_puro_e_nao_o_client(repo):
    """D1: `models`/`ports` de integracao nao fazem I/O e podem ir para application/; o client nao."""
    from revold_tooling.generate import render_importlinter

    _integration_with_modules(repo, '["models"]')
    write_unit(
        repo,
        "libs/domains/dom",
        unit_yaml("dom", "domain", '["platform", "svc"]'),
        "revold-dom",
        "revold_dom",
        '"revold-platform", "revold-svc"',
    )
    _add_source(repo, "revold-dom")

    text = render_importlinter(load_manifest(repo))
    io_contract = text.split("name = dom: integracao com I/O so entra pela camada adapters")[
        1
    ].split("[importlinter")[0]
    domain_contract = text.split("name = dom: dominio nao importa integracao")[1].split(
        "[importlinter"
    )[0]

    assert "revold_svc.client" in io_contract and "revold_svc.models" not in io_contract
    assert "revold_dom.application" in io_contract and "revold_dom.ports" in io_contract
    assert "    revold_svc\n" in domain_contract


# --------------------------------------------------------------------- stages
def _product_with_stages(repo: Path, stages: str) -> None:
    directory = write_unit(
        repo,
        "products/prod",
        unit_yaml("prod", "product", '["platform"]', extra=f"stages: {stages}\n"),
        "revold-prod",
        "revold_prod",
        '"revold-platform"',
    )
    for name in ("application", "application/a", "application/b", "application/c"):
        (directory / "src" / "revold_prod" / name).mkdir(parents=True, exist_ok=True)
        (directory / "src" / "revold_prod" / name / "__init__.py").write_text("", encoding="utf-8")
    _add_source(repo, "revold-prod")


def test_stages_viram_contrato_de_camadas_da_application(repo):
    from revold_tooling.generate import render_importlinter

    _product_with_stages(repo, '["a", "b | c"]')
    # O gerador so escreve contrato de camada quando ha integracao no repo.
    _integration_with_modules(repo, '["models"]')

    text = render_importlinter(load_manifest(repo))
    contract = text.split("name = prod: etapas")[1].split("[importlinter")[0]

    assert "type = layers" in contract
    assert "    revold_prod.application\n" in contract
    assert contract.split("layers =")[1].split() == ["a", "b", "|", "c"]


def test_stage_que_nao_existe_reprova(repo):
    _product_with_stages(repo, '["a", "nao_existe"]')

    assert "stages cita ['nao_existe']" in _problems(repo)


def test_stages_so_vale_em_domain_e_product(repo):
    write_unit(
        repo,
        "libs/capabilities/c",
        unit_yaml("c", "capability", '["platform"]', extra='stages: ["x"]\n'),
        "revold-c",
        "revold_c",
        '"revold-platform"',
    )
    _add_source(repo, "revold-c")

    assert "`stages` so vale em domain e product" in _problems(repo)
