"""Gates que valem para toda unidade do monorepo.

1. **Ninguém lê ambiente fora do lugar.** Só o `settings.py` de cada app e
   `libs/platform/.../configuration/` leem `os.environ` ou `os.getenv`. Leitura no import
   congela o valor, some do resumo de configuração e esconde dependência morta.
2. **Nenhuma pasta `testing/` em unidade.** Adapter em memória mora em `adapters/` (ou em
   `adapters/memory/`): o app usa ele no modo local, e produção não deve importar "testing".
   As fábricas de dados de teste moram em `tests/support/`, fora de toda unidade.
3. **Toda unidade nasce completa**: manifesto, empacotamento, README e testes.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from revold_tooling.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = load_manifest(ROOT)
UNITS = list(MANIFEST.units)
PYTHON_UNITS = [u for u in UNITS if u.is_python]

_ENV_NAMES = frozenset({"environ", "getenv", "getenvb", "environb"})
_CONFIGURATION_DIR = "libs/platform/src/revold_platform/configuration/"


def _sources() -> list[Path]:
    files: list[Path] = []
    for unit in PYTHON_UNITS:
        if unit.src_dir.is_dir():
            files.extend(p for p in unit.src_dir.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(files)


def _may_read_environment(path: Path) -> bool:
    """O parser da plataforma e o `settings.py` na raiz do pacote de um app."""
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith(_CONFIGURATION_DIR):
        return True
    return (
        rel.startswith("apps/") and path.name == "settings.py" and path.parent.parent.name == "src"
    )


def _env_reads(path: Path) -> list[str]:
    """Leituras de ambiente no CÓDIGO (docstring e comentário não contam)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "os" and node.attr in _ENV_NAMES:
                found.add(f"linha {node.lineno}: os.{node.attr}")
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            names = {alias.name for alias in node.names} & _ENV_NAMES
            if names:
                found.add(f"linha {node.lineno}: from os import {', '.join(sorted(names))}")
    return sorted(found)


def test_there_are_units_to_check():
    """Guarda contra o gate passar por engano se a estrutura mudar."""
    assert len(PYTHON_UNITS) >= 20
    assert len(_sources()) > 100


@pytest.mark.parametrize("path", _sources(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_unit_does_not_read_environment(path):
    if _may_read_environment(path):
        pytest.skip("lugar de ler ambiente: settings.py do app ou a configuration da plataforma")
    reads = _env_reads(path)
    assert not reads, (
        f"{path.relative_to(ROOT).as_posix()} le variavel de ambiente: {reads}. "
        "Receba o valor por parametro; quem le o ambiente e o settings.py do app."
    )


@pytest.mark.parametrize("unit", [u for u in PYTHON_UNITS if u.kind == "app"], ids=lambda u: u.id)
def test_python_app_has_a_settings_module(unit):
    assert (
        unit.src_dir / unit.import_name / "settings.py"
    ).is_file(), f"{unit.id}: app Python sem settings.py, o unico modulo que le o ambiente"


@pytest.mark.parametrize("unit", UNITS, ids=lambda u: u.id)
def test_unit_has_no_testing_folder(unit):
    found = [
        p.relative_to(ROOT).as_posix()
        for p in unit.directory.rglob("testing")
        if p.is_dir() and "node_modules" not in p.parts
    ]
    assert not found, f"pasta testing/ em unidade: {found}. Apoio de teste vai em tests/support/."


@pytest.mark.parametrize("unit", UNITS, ids=lambda u: u.id)
def test_unit_is_born_complete(unit):
    """Unidade tem unit.yaml, empacotamento, README e teste.

    Unidade TypeScript troca o pyproject por um `package.json` com os scripts de lint e de
    teste; o teste de site hoje é o E2E do Playwright, ou nenhum, e isso fica declarado no script.
    """
    assert (unit.directory / "README.md").is_file(), f"{unit.id}: sem README.md"
    if unit.language == "typescript":
        package = json.loads((unit.directory / "package.json").read_text(encoding="utf-8"))
        scripts = package.get("scripts", {})
        assert {"lint", "test"} <= set(
            scripts
        ), f"{unit.id}: package.json sem script de lint ou de teste"
        return
    assert (unit.directory / "pyproject.toml").is_file()
    assert unit.pyproject["project"]["requires-python"] == ">=3.12"
    assert unit.pyproject["project"]["version"], f"{unit.id}: sem versao"
    tests = [p for p in (unit.directory / "tests").glob("test_*.py")]
    assert tests, f"{unit.id}: nenhum teste em {unit.rel_dir}/tests"


def test_env_detector_catches_both_spellings(tmp_path):
    """O detector precisa enxergar `os.getenv` e `from os import environ`."""
    sample = tmp_path / "x.py"
    sample.write_text("import os\nfrom os import environ\nA = os.getenv('A')\n", encoding="utf-8")
    assert len(_env_reads(sample)) == 2
