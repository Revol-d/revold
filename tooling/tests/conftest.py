"""Um monorepo de mentira, para o tooling ler e escrever sem tocar no de verdade."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from tooling_helpers import ROOT_PYPROJECT, unit_yaml, write_unit

REAL_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Raiz com o schema, os modelos, o repo.yaml e uma unidade `platform`."""
    (tmp_path / "tooling").mkdir()
    shutil.copytree(REAL_ROOT / "tooling" / "schema", tmp_path / "tooling" / "schema")
    shutil.copytree(REAL_ROOT / "tooling" / "templates", tmp_path / "tooling" / "templates")
    shutil.copy(REAL_ROOT / "tooling" / "repo.yaml", tmp_path / "tooling" / "repo.yaml")
    (tmp_path / ".github").mkdir()
    (tmp_path / "pyproject.toml").write_text(ROOT_PYPROJECT, encoding="utf-8")
    write_unit(
        tmp_path,
        "libs/platform",
        unit_yaml("platform", "platform"),
        "revold-platform",
        "revold_platform",
    )
    return tmp_path
