"""Fecho, BOM e o gate de versao do `dev check` (ADR-0029).

O gate de versao e o que impede o mesmo numero de versao de ter dois conteudos. Os testes montam
um repositorio de mentira, gravam um release e mudam codigo depois dele.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from revold_tooling.manifest import load_manifest
from revold_tooling.release import (
    Bom,
    BomEntry,
    bump,
    compute_bom,
    next_version,
    release_tag,
    released_bom,
    report_release,
    set_version,
    sha256_of_source,
    verify_release,
    write_release,
)
from revold_tooling.version_gate import stale_versions
from tooling_helpers import unit_yaml, write_unit

ROOT = Path(__file__).resolve().parents[2]


def test_real_app_closure_is_install_order_and_includes_transitive_deps():
    manifest = load_manifest(ROOT)
    closure = [u.id for u in manifest.closure("event-worker")]
    assert closure[-1] == "event-worker"
    # O fecho leva o que entra so de forma transitiva: `smtp` nao esta no depends_on do worker,
    # entra pelo dominio `notification`. Ficar fora da imagem quebraria no primeiro e-mail.
    assert "smtp" not in manifest.by_id["event-worker"].depends_on
    assert "smtp" in closure
    for position, unit_id in enumerate(closure):
        for dep in manifest.by_id[unit_id].depends_on:
            assert closure.index(dep) < position, f"{dep} precisa vir antes de {unit_id}"


def test_bom_round_trip_is_byte_stable():
    bom = Bom(
        app="job",
        versao="1.0.0",
        unidades=(BomEntry("revold-core", "0.1.0", "ab" * 32),),
        lock_sha256="cd" * 32,
    )
    assert Bom.from_json(bom.to_json()) == bom
    assert Bom.from_json(bom.to_json()).to_json() == bom.to_json()


def test_bom_with_unknown_schema_is_refused():
    with pytest.raises(ValueError, match="schema"):
        Bom.from_json(json.dumps({"schema": 99, "app": "x", "versao": "1", "unidades": []}))


def test_report_lists_what_changed_version(capsys):
    previous = Bom(
        app="job",
        versao="1.0.0",
        unidades=(BomEntry("revold-core", "0.1.0", "s"), BomEntry("job", "1.0.0", "s")),
    )
    bom = Bom(
        app="job",
        versao="1.0.1",
        unidades=(BomEntry("revold-core", "0.2.0", "s"), BomEntry("job", "1.0.1", "s")),
    )
    assert report_release(previous, bom) == ["job", "revold-core"]
    assert "revold-core 0.1.0 -> 0.2.0" in capsys.readouterr().out


def test_report_of_a_first_release_says_so(capsys):
    bom = Bom(app="job", versao="0.1.0", unidades=(BomEntry("job", "0.1.0", "s"),))
    report_release(None, bom)
    assert "Primeiro release" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("current", "part", "expected"),
    [
        ("0.2.9", "patch", "0.2.10"),
        ("0.2.9", "minor", "0.3.0"),
        ("0.2.9", "major", "1.0.0"),
        ("0.2.9", "2.0.0", "2.0.0"),
    ],
)
def test_next_version(current, part, expected):
    assert next_version(current, part) == expected


def test_next_version_refuses_an_unknown_part():
    with pytest.raises(ValueError, match="Parte invalida"):
        next_version("0.1.0", "gigante")


def test_release_tag_is_app_at_version():
    assert release_tag(Bom(app="api-gateway", versao="0.3.1", unidades=())) == "api-gateway@0.3.1"


# --------------------------------------------------------------------- conteudo
def test_source_hash_ignores_line_endings_and_bytecode(tmp_path):
    """O checkout do Windows entrega CRLF e o runner do CI, LF: o sha256 tem que ser o mesmo."""
    lf, crlf = tmp_path / "lf" / "src", tmp_path / "crlf" / "src"
    for directory, newline in ((lf, b"\n"), (crlf, b"\r\n")):
        (directory / "pkg").mkdir(parents=True)
        (directory / "pkg" / "__init__.py").write_bytes(b"X = 1" + newline + b"Y = 2" + newline)
    (crlf / "pkg" / "__pycache__").mkdir()
    (crlf / "pkg" / "__pycache__" / "__init__.cpython-312.pyc").write_bytes(b"\x00\x01")

    assert sha256_of_source(lf) == sha256_of_source(crlf)


def test_source_hash_changes_when_a_file_moves(tmp_path):
    first, second = tmp_path / "a" / "src", tmp_path / "b" / "src"
    (first / "pkg").mkdir(parents=True)
    (second / "pkg" / "sub").mkdir(parents=True)
    (first / "pkg" / "mod.py").write_text("X = 1\n", encoding="utf-8")
    (second / "pkg" / "sub" / "mod.py").write_text("X = 1\n", encoding="utf-8")

    assert sha256_of_source(first) != sha256_of_source(second)


# --------------------------------------------------------------------- gate de versao
@pytest.fixture
def released_repo(repo: Path) -> Path:
    """Repositorio com `core` -> `job` e um release gravado."""
    with (repo / "pyproject.toml").open("a", encoding="utf-8") as handle:
        handle.write("revold-core = { workspace = true }\n")
    write_unit(
        repo,
        "libs/capabilities/core",
        unit_yaml("core", "capability"),
        "revold-core",
        "revold_core",
    )
    write_unit(
        repo,
        "apps/loja/job",
        unit_yaml("job", "app", depends_on='["core"]', extra="runtime: celery-worker\n"),
        "job",
        "job",
        deps='"revold-core"',
    )
    (repo / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    manifest = load_manifest(repo)
    app = manifest.by_id["job"]
    write_release(manifest, app, compute_bom(manifest, app))
    return repo


def test_release_file_round_trips_through_the_gate(released_repo):
    manifest = load_manifest(released_repo)
    path, bom = released_bom(manifest, manifest.by_id["job"])
    assert path == released_repo / ".releases" / "job.json"
    assert bom is not None and [e.unidade for e in bom.unidades] == ["revold-core", "job"]
    assert stale_versions(manifest) == ([], [])


def test_code_change_without_bump_fails(released_repo):
    (released_repo / "libs/capabilities/core/src/revold_core/__init__.py").write_text(
        "X = 1\n", encoding="utf-8"
    )
    stale, _ = stale_versions(load_manifest(released_repo))
    assert [s.unit for s in stale] == ["core"]
    assert "dev bump core patch" in str(stale[0])


def test_code_change_with_bump_passes(released_repo):
    (released_repo / "libs/capabilities/core/src/revold_core/__init__.py").write_text(
        "X = 1\n", encoding="utf-8"
    )
    set_version(released_repo / "libs/capabilities/core/pyproject.toml", "0.1.1")
    assert stale_versions(load_manifest(released_repo))[0] == []


def test_tests_and_readme_do_not_count_as_code(released_repo):
    (released_repo / "libs/capabilities/core/tests").mkdir()
    (released_repo / "libs/capabilities/core/tests/test_x.py").write_text("", encoding="utf-8")
    (released_repo / "libs/capabilities/core/README.md").write_text("doc\n", encoding="utf-8")
    assert stale_versions(load_manifest(released_repo))[0] == []


def test_app_code_change_is_left_to_the_release(released_repo):
    (released_repo / "apps/loja/job/src/job/__init__.py").write_text("Y = 2\n", encoding="utf-8")
    assert stale_versions(load_manifest(released_repo))[0] == []


def test_app_without_release_is_skipped_out_loud(repo):
    """Gate que pula calado parece protecao e nao e: sem release, ele precisa DIZER que pulou."""
    write_unit(
        repo,
        "apps/loja/job",
        unit_yaml("job", "app", extra="runtime: celery-worker\n"),
        "job",
        "job",
    )
    stale, notes = stale_versions(load_manifest(repo))
    assert stale == []
    assert notes == ["job ainda nao tem release (.releases/job.json): nada a comparar"]


def test_bump_touches_only_the_requested_unit(released_repo):
    assert bump(load_manifest(released_repo), "core", "minor") == "0.2.0"
    manifest = load_manifest(released_repo)
    assert manifest.by_id["core"].version == "0.2.0"
    assert manifest.by_id["job"].version == "0.1.0"
    assert manifest.by_id["platform"].version == "0.1.0"


# --------------------------------------------------------------------- conferencia do release
def test_verify_release_accepts_the_code_the_bom_describes(released_repo):
    manifest = load_manifest(released_repo)
    assert verify_release(manifest, manifest.by_id["job"]) == []


def test_verify_release_catches_code_that_changed_after_the_bom(released_repo):
    (released_repo / "apps/loja/job/src/job/__init__.py").write_text("Y = 2\n", encoding="utf-8")
    manifest = load_manifest(released_repo)
    problems = verify_release(manifest, manifest.by_id["job"])
    assert problems == ["job 0.1.0: o conteudo do src/ nao e o que o BOM aprovou"]


def test_verify_release_catches_a_lock_that_changed_after_the_bom(released_repo):
    (released_repo / "uv.lock").write_text("version = 2\n", encoding="utf-8")
    manifest = load_manifest(released_repo)
    assert verify_release(manifest, manifest.by_id["job"]) == ["uv.lock: nao e o que o BOM aprovou"]


def test_verify_release_without_a_bom_says_so(repo):
    write_unit(
        repo,
        "apps/loja/job",
        unit_yaml("job", "app", extra="runtime: celery-worker\n"),
        "job",
        "job",
    )
    manifest = load_manifest(repo)
    assert verify_release(manifest, manifest.by_id["job"]) == [
        "job: nao ha `.releases/job.json` para conferir"
    ]
