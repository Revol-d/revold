"""Construtores de unidades de mentira para os testes do tooling."""

from __future__ import annotations

from pathlib import Path

ROOT_PYPROJECT = """\
[tool.uv.workspace]
members = [
    "libs/platform",
    "libs/integrations/*",
    "libs/capabilities/*",
    "libs/domains/*",
    "products/*",
]

[tool.uv.sources]
revold-platform = { workspace = true }
"""


def write_unit(
    root: Path, rel_dir: str, unit_yaml: str, dist: str, import_name: str, deps: str = ""
) -> Path:
    """Grava uma unidade Python minima: unit.yaml, pyproject.toml e o pacote em src/."""
    directory = root / rel_dir
    (directory / "src" / import_name).mkdir(parents=True)
    (directory / "src" / import_name / "__init__.py").write_text(
        "__all__: list[str] = []\n", encoding="utf-8"
    )
    (directory / "unit.yaml").write_text(unit_yaml, encoding="utf-8")
    (directory / "pyproject.toml").write_text(
        f'[project]\nname = "{dist}"\nversion = "0.1.0"\ndependencies = [{deps}]\n',
        encoding="utf-8",
    )
    return directory


def unit_yaml(
    unit_id: str, kind: str, depends_on: str = "[]", lifecycle: str = "pilot", extra: str = ""
) -> str:
    """Texto de um unit.yaml valido, com o minimo de campos."""
    product = "loja" if kind in {"app", "product"} else ""
    return (
        f"id: {unit_id}\nkind: {kind}\nproduct: {product}\nlanguage: python\nlifecycle: {lifecycle}\n"
        f'owners: ["@dono"]\ndepends_on: {depends_on}\n{extra}'
    )
