"""Gate: um app só importa as unidades que declara em `depends_on`, e nunca outro app.

O import-linter não cobre os apps: o app é o composition root e fica fora dos contratos de
camada. Sobra um risco que só aparece na imagem: no ambiente de desenvolvimento **todas** as
unidades estão instaladas, então um `import` de uma unidade que o app não declarou funciona na
máquina e no pytest. A imagem do app é montada com `uv sync --package <app>`, que instala só o
fecho declarado, e o mesmo `import` quebra em produção com `ModuleNotFoundError`.

Este teste lê o código do app e confere cada `import` contra o `depends_on` do `unit.yaml`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from revold_tooling.manifest import Unit, load_manifest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = load_manifest(ROOT)
PYTHON_APPS = [u for u in MANIFEST.units if u.kind == "app" and u.is_python]
UNIT_BY_IMPORT = {u.import_name: u for u in MANIFEST.python_units if u.import_name}


def _imported_units(path: Path) -> set[str]:
    """Os pacotes de unidade que o arquivo importa (o primeiro nome de cada `import`)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names & set(UNIT_BY_IMPORT)


def _app_imports(app: Unit) -> dict[str, set[str]]:
    """Pacote de unidade importado -> arquivos do app que o importam."""
    found: dict[str, set[str]] = {}
    for path in app.src_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for name in _imported_units(path):
            found.setdefault(name, set()).add(path.relative_to(ROOT).as_posix())
    return found


def test_there_are_python_apps_to_check():
    assert len(PYTHON_APPS) >= 3


@pytest.mark.parametrize("app", PYTHON_APPS, ids=lambda u: u.id)
def test_app_does_not_import_another_app(app):
    other_apps = {u.import_name for u in PYTHON_APPS if u.id != app.id}
    offenders = {
        name: sorted(files) for name, files in _app_imports(app).items() if name in other_apps
    }
    assert not offenders, (
        f"{app.id} importa outro app: {offenders}. O que dois apps precisam mora no produto "
        "ou numa lib; app nao depende de app."
    )


@pytest.mark.parametrize("app", PYTHON_APPS, ids=lambda u: u.id)
def test_app_imports_only_what_it_declares(app):
    allowed = {MANIFEST.by_id[d].import_name for d in app.depends_on} | {app.import_name}
    offenders = {
        name: sorted(files) for name, files in _app_imports(app).items() if name not in allowed
    }
    assert not offenders, (
        f"{app.id} importa unidade fora do depends_on: {offenders}. Funciona na maquina, onde "
        "tudo esta instalado, e quebra na imagem, que so leva o fecho declarado. Declare no "
        "unit.yaml e no pyproject.toml do app."
    )


@pytest.mark.parametrize("app", PYTHON_APPS, ids=lambda u: u.id)
def test_app_declares_only_what_it_imports(app):
    """Dependência declarada e nunca importada engorda a imagem e o fecho do release à toa."""
    imported = set(_app_imports(app))
    declared = {MANIFEST.by_id[d].import_name for d in app.depends_on}
    unused = sorted(declared - imported)
    assert (
        not unused
    ), f"{app.id} declara e nao importa: {unused}. Tire do unit.yaml e do pyproject.toml."


def test_the_detector_sees_both_import_forms(tmp_path):
    """Prova que o teste falharia: sem isto, ele poderia estar sempre verde."""
    sample = tmp_path / "x.py"
    sample.write_text(
        "import revold_cart.domain\nfrom revold_catalog.ports import ProductRepository\nimport json\n",
        encoding="utf-8",
    )
    assert _imported_units(sample) == {"revold_cart", "revold_catalog"}
