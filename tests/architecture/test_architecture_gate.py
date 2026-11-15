"""Gate de arquitetura: o `.importlinter` é gerado dos `unit.yaml`, nunca editado (ADR-0030).

Dois riscos que estes testes cobrem:

1. alguém editar o `.importlinter` (ou o CODEOWNERS) à mão e ele divergir do manifesto;
2. um contrato **sumir** silenciosamente: o arquivo continua válido, o CI fica verde, e a
   fronteira deixa de ser verificada sem ninguém perceber.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest
from revold_tooling.generate import stale_generated
from revold_tooling.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[2]
IMPORTLINTER = ROOT / ".importlinter"
MANIFEST = load_manifest(ROOT)
LINTED = [u for u in MANIFEST.python_units if u.kind != "app"]


def _contracts() -> dict[str, dict]:
    parser = configparser.ConfigParser()
    parser.read(IMPORTLINTER, encoding="utf-8")
    return {
        parser[s]["name"]: dict(parser[s])
        for s in parser.sections()
        if s.startswith("importlinter:contract:")
    }


def _root_packages() -> set[str]:
    parser = configparser.ConfigParser()
    parser.read(IMPORTLINTER, encoding="utf-8")
    return set(parser["importlinter"]["root_packages"].split())


def test_generated_files_are_in_sync_with_the_manifest():
    """Se divergir, o gate está validando uma arquitetura que não é a declarada."""
    stale = [p.as_posix() for p in stale_generated(MANIFEST)]
    assert not stale, f"{stale} fora de dia com os unit.yaml. Regenere com `uv run dev gen`."


def test_every_library_unit_is_linted():
    expected = {u.import_name for u in LINTED}
    assert expected <= _root_packages(), f"fora do lint: {expected - _root_packages()}"


@pytest.mark.parametrize("unit", LINTED, ids=lambda u: u.id)
def test_every_unit_has_its_dependency_contract(unit):
    """Um contrato removido não quebra o arquivo: some silenciosamente."""
    allowed = {MANIFEST.by_id[d].import_name for d in unit.depends_on}
    others = {u.import_name for u in LINTED if u.id != unit.id}
    contract = _contracts().get(f"{unit.id} so importa o que declara em depends_on")
    if not others - allowed:
        # Quem depende de todas as outras unidades não tem o que proibir, e o gerador não
        # escreve contrato vazio.
        assert contract is None, f"contrato de dependencia de {unit.id} sem nada a proibir"
        return
    assert contract, f"contrato de dependencia de {unit.id} ausente"
    assert set(contract["forbidden_modules"].split()) == others - allowed


@pytest.mark.parametrize("unit", [u for u in MANIFEST.units if u.is_layered], ids=lambda u: u.id)
def test_layered_units_have_layer_and_integration_contracts(unit):
    contracts = _contracts()
    layers = contracts.get(f"{unit.id}: camadas")
    assert layers, f"contrato de camadas de {unit.id} ausente"
    assert layers["layers"].split() == ["adapters", "application", "ports", "domain"]
    # São dois: domínio fechado para integração, e application/ports abertos só para os
    # `pure_modules` que a integração declara.
    domain = contracts.get(f"{unit.id}: dominio nao importa integracao")
    io = contracts.get(f"{unit.id}: integracao com I/O so entra pela camada adapters")
    assert domain and domain["source_modules"].split() == [f"{unit.import_name}.domain"]
    assert io and io["source_modules"].split() == [
        f"{unit.import_name}.application",
        f"{unit.import_name}.ports",
    ]
    integrations = [u for u in MANIFEST.python_units if u.kind == "integration"]
    assert set(domain["forbidden_modules"].split()) == {u.import_name for u in integrations}
    for integration in integrations:
        for pure in integration.pure_modules:
            assert f"{integration.import_name}.{pure}" not in io["forbidden_modules"].split()


@pytest.mark.parametrize("unit", [u for u in MANIFEST.units if u.is_layered], ids=lambda u: u.id)
def test_layered_units_have_the_four_layers_on_disk(unit):
    """Camada que não existe no disco faz o import-linter reprovar com uma mensagem obscura."""
    package = unit.src_dir / unit.import_name
    missing = [
        layer
        for layer in ("adapters", "application", "ports", "domain")
        if not (package / layer / "__init__.py").is_file()
    ]
    assert not missing, f"{unit.id}: camadas sem __init__.py: {missing}"


def test_app_is_not_linted():
    """O composition root é isento por desenho: é o único que importa tudo."""
    apps = {u.import_name for u in MANIFEST.units if u.kind == "app" and u.is_python}
    assert not (apps & _root_packages()), "app nao deve estar sob contrato de lint"
