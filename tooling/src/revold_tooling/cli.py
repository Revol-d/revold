"""`uv run dev <comando>`: a ferramenta de desenvolvimento do monorepo (ADR-0030).

    dev check [--no-mypy]                 manifesto, gerados em dia, versoes, import-linter e mypy
    dev gen                               regenera .importlinter e CODEOWNERS dos unit.yaml
    dev affected [--base REF] [--json]    unidades afetadas pela branch (e consumidores)
    dev test [--affected] [--base REF]    testes (todos, ou so os afetados)
    dev new <kind> <id> [--runtime R] [--dry-run]  cria unidade de tooling/templates/
    dev version                           versao de cada unidade
    dev bump <unidade> <parte>            sobe a versao de UMA unidade
    dev build <app> [--image] | [<unidade> ...]  BOM do fecho em dist/<app>/, ou wheels em dist/
    dev lint-imports                      so o import-linter
    dev release <app> <parte> [--dry-run] testa o fecho, sobe o app e grava o BOM
    dev verify-release <app>              confere o BOM gravado contra o codigo (o release.yml usa)

`dev check` e o mesmo no hook e no CI: um gate so, uma linha so.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from revold_tooling import affected as affected_mod
from revold_tooling import release as release_mod
from revold_tooling import version_gate
from revold_tooling.generate import stale_generated, write_generated
from revold_tooling.manifest import Manifest, ManifestError, load_manifest
from revold_tooling.scaffold import APP_RUNTIMES, NewUnit, create_unit

# Os flags do mypy. O alvo sai do manifesto: o `src/` de cada unidade Python e o do tooling.
# Passar `apps/` e `libs/` inteiros faria o mypy varrer `node_modules` dos sites e as pastas
# `tests/`, que repetem nome de modulo (`conftest`, `test_domain`) entre as unidades.
MYPY_FLAGS = ("--ignore-missing-imports",)
TOOLING_SRC = "tooling/src"

# A suite central: o que testa o repositorio inteiro, e nao uma unidade.
CENTRAL_TEST_DIRS = ("tests/architecture", "tooling/tests")
# Pastas de teste dentro de uma unidade. `evals/` e do assistente de IA (marcador `eval`).
UNIT_TEST_DIRS = ("tests", "evals")


def find_root(start: Path | None = None) -> Path:
    """A raiz do repositorio: a primeira pasta acima com `tooling/repo.yaml`."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "tooling" / "repo.yaml").is_file():
            return candidate
    raise SystemExit(
        "Nao achei a raiz do monorepo (tooling/repo.yaml). Rode dentro do repositorio."
    )


def _manifest(root: Path) -> Manifest:
    try:
        return load_manifest(root)
    except ManifestError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc


def _source_paths(manifest: Manifest) -> list[str]:
    return [str(u.src_dir) for u in manifest.python_units if u.src_dir.is_dir()]


# --------------------------------------------------------------------- comandos
def cmd_gen(args: argparse.Namespace, root: Path) -> int:
    """Regenera os arquivos derivados do manifesto."""
    changed = write_generated(_manifest(root))
    print(
        "Atualizados: " + ", ".join(p.as_posix() for p in changed)
        if changed
        else "Nada a atualizar."
    )
    return 0


def cmd_lint_imports(args: argparse.Namespace, root: Path) -> int:
    """Roda o import-linter com o `src/` de todas as unidades no caminho."""
    manifest = _manifest(root)
    return _lint_imports(manifest)


def _lint_imports(manifest: Manifest) -> int:
    # NAO troque por `-m importlinter.cli`: o pacote nao tem __main__.py, o comando nunca
    # executa e o processo sai 0 SEM verificar contrato nenhum (falso verde). O `src/` de
    # cada unidade vai no caminho para o grafo enxergar o fonte mesmo fora do venv.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    env["PYTHONPATH"] = os.pathsep.join([*_source_paths(manifest), env.get("PYTHONPATH", "")])
    config = str(manifest.root / ".importlinter")
    code = f"import sys; from importlinter.cli import lint_imports; sys.exit(lint_imports(config_filename={config!r}))"
    return subprocess.call([sys.executable, "-c", code], cwd=manifest.root, env=env)


def cmd_check(args: argparse.Namespace, root: Path) -> int:
    """O gate unico: manifesto, gerados em dia, versoes, import-linter e mypy."""
    manifest = _manifest(root)
    print(f"Manifesto: {len(manifest.units)} unidades validas.", flush=True)

    stale = stale_generated(manifest)
    if stale:
        print(
            "Gerados fora de dia: "
            + ", ".join(p.as_posix() for p in stale)
            + ". Rode `uv run dev gen` e commite.",
            file=sys.stderr,
        )
        return 1
    print("Gerados em dia: .importlinter e .github/CODEOWNERS.", flush=True)

    if _check_versions(manifest) != 0:
        return 1
    if _lint_imports(manifest) != 0:
        return 1
    if args.no_mypy:
        return 0
    return _mypy(manifest)


def _mypy(manifest: Manifest) -> int:
    targets = [Path(p).relative_to(manifest.root).as_posix() for p in _source_paths(manifest)]
    if (manifest.root / TOOLING_SRC).is_dir():
        targets.append(TOOLING_SRC)
    return subprocess.call([sys.executable, "-m", "mypy", *targets, *MYPY_FLAGS], cwd=manifest.root)


def _check_versions(manifest: Manifest) -> int:
    """Codigo mudou desde o ultimo release e a versao nao subiu? Falha."""
    stale, notes = version_gate.stale_versions(manifest)
    for note in notes:
        print(f"Gate de versao: {note}.", flush=True)
    if stale:
        print("Mesmo numero, outro conteudo:", file=sys.stderr)
        for item in stale:
            print(f"  {item}", file=sys.stderr)
        return 1
    if notes:
        print("Versoes: nenhuma divergencia nos apps que ja tem release.", flush=True)
    else:
        print(
            "Versoes em dia: nenhum src/ mudou sem a versao subir desde o ultimo release.",
            flush=True,
        )
    return 0


def cmd_affected(args: argparse.Namespace, root: Path) -> int:
    """Lista as unidades afetadas pela branch."""
    manifest = _manifest(root)
    files = args.files if args.files else affected_mod.changed_files(manifest, args.base)
    result = affected_mod.compute_affected(manifest, files)
    if args.json:
        # `web`: alguma unidade TypeScript afetada. O job de frontend do CI so roda com ele.
        web = any(not manifest.by_id[u].is_python for u in result.units)
        python = any(manifest.by_id[u].is_python for u in result.units)
        payload = {
            "units": list(result.units),
            "any": result.any,
            "global": result.global_change,
            "web": web,
            "python": python,
        }
        print(json.dumps(payload))
    else:
        for unit_id in result.units:
            print(unit_id)
    return 0


def cmd_test(args: argparse.Namespace, root: Path) -> int:
    """Testes: a suite inteira, ou so os das unidades afetadas."""
    manifest = _manifest(root)
    if not args.affected:
        targets = [*CENTRAL_TEST_DIRS, *(_unit_test_dirs(manifest, [u.id for u in manifest.units]))]
        return _run_tests(manifest, targets, args.pytest_args)
    result = affected_mod.compute_affected(
        manifest, affected_mod.changed_files(manifest, args.base)
    )
    print("Afetadas: " + (", ".join(result.units) or "nenhuma"), flush=True)
    return _run_tests(
        manifest, _targets_for(manifest, list(result.units), result.global_change), args.pytest_args
    )


def _targets_for(manifest: Manifest, unit_ids: list[str], global_change: bool = False) -> list[str]:
    """As pastas de teste destas unidades; com mudanca global, a suite central junto."""
    targets = _unit_test_dirs(manifest, unit_ids)
    return [*CENTRAL_TEST_DIRS, *targets] if global_change else targets


def _run_tests(manifest: Manifest, targets: list[str], pytest_args: list[str]) -> int:
    root = manifest.root
    targets = [t for t in dict.fromkeys(targets) if (root / t).exists()]
    if not targets:
        print("Nenhum teste Python a rodar.", flush=True)
        return 0
    paths = [*_source_paths(manifest), os.environ.get("PYTHONPATH", "")]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(paths)}
    return subprocess.call(
        [sys.executable, "-m", "pytest", *targets, *pytest_args], cwd=root, env=env
    )


def _unit_test_dirs(manifest: Manifest, unit_ids: list[str]) -> list[str]:
    dirs = []
    for unit_id in unit_ids:
        # Unidade TypeScript testa pelo pnpm (job de frontend do CI); o pytest nao a coleta.
        if not manifest.by_id[unit_id].is_python:
            continue
        for name in UNIT_TEST_DIRS:
            tests = manifest.by_id[unit_id].directory / name
            if tests.is_dir():
                dirs.append(tests.relative_to(manifest.root).as_posix())
    return dirs


def cmd_new(args: argparse.Namespace, root: Path) -> int:
    """Cria uma unidade nova (ou so mostra o que criaria, com `--dry-run`)."""
    request = NewUnit(
        kind=args.kind,
        id=args.id,
        depends_on=tuple(args.depends_on),
        product=args.product,
        lifecycle=args.lifecycle,
        description=args.description or "",
        runtime=args.runtime,
    )
    try:
        created = create_unit(root, request, dry_run=args.dry_run)
    except (ValueError, ManifestError) as exc:
        print(f"Nada foi criado. {exc}", file=sys.stderr)
        return 1
    rel = created.target.relative_to(root).as_posix()
    print(f"{'Criaria' if args.dry_run else 'Criada'} {rel}/ com {len(created.files)} arquivo(s):")
    for name in created.files:
        print(f"  {name}")
    if created.added_dependencies:
        print(
            "depends_on ganhou "
            + ", ".join(created.added_dependencies)
            + " (o codigo do modelo usa)."
        )
    for change in created.root_changes:
        print(f"{'Mudaria' if args.dry_run else 'Mudou'}: {change}")
    if args.dry_run:
        print("Dry-run: nada foi escrito.")
    else:
        print("Proximo passo: `uv sync` para instalar a unidade no ambiente.")
    return 0


def cmd_version(args: argparse.Namespace, root: Path) -> int:
    """Versao de cada unidade."""
    release_mod.print_versions(_manifest(root))
    return 0


def cmd_bump(args: argparse.Namespace, root: Path) -> int:
    """Sobe a versao de UMA unidade."""
    try:
        release_mod.bump(_manifest(root), args.unit, args.part)
    except (KeyError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    # O uv.lock registra a versao de cada membro: commite o pyproject.toml e o lock juntos.
    return release_mod.refresh_lock(root)


def cmd_build(args: argparse.Namespace, root: Path) -> int:
    """Um app: o BOM do fecho em `dist/<app>/` (e a imagem, com `--image`). Outras: so o wheel."""
    manifest = _manifest(root)
    if args.all_apps:
        if args.units:
            print("`--all-apps` nao combina com nomes de unidade.", file=sys.stderr)
            return 1
        args.units = [u.id for u in manifest.units if u.kind == "app" and u.is_python]
    try:
        units = [manifest.find(n) for n in args.units]
    except KeyError as exc:
        print(exc, file=sys.stderr)
        return 1
    apps = [u for u in units if u.kind == "app"]
    if apps and len(apps) != len(units):
        print(
            "Misture nao: `dev build <app>` monta o fecho; `dev build <unidade>...` so os wheels.",
            file=sys.stderr,
        )
        return 1
    try:
        for app in apps:
            release_mod.build_app(manifest, app, image=args.image)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if not apps:
        release_mod.build(manifest, args.units)
    return 0


def cmd_release(args: argparse.Namespace, root: Path) -> int:
    """Prova o fecho (testes, versoes e fronteiras), sobe o app e grava o BOM.

    A tag `<app>@<versao>` NAO nasce aqui: o ruleset `tags-de-release` so deixa o GitHub
    Actions cria-la. Ela sai do `release.yml` quando o PR com `.releases/<app>.json` entra
    na `main`, e o mesmo workflow confere o BOM contra o codigo que entrou.
    """
    manifest = _manifest(root)
    try:
        app = manifest.find(args.app)
        new_version = release_mod.next_version(app.version, args.part)
    except (KeyError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    if app.kind != "app":
        print(f"{app.id!r} nao e um app. Release e so de app.", file=sys.stderr)
        return 1
    if not app.is_python:
        print(
            f"{app.id!r} e TypeScript: o release pelo tooling so cobre app Python.", file=sys.stderr
        )
        return 1
    closure = [u.id for u in manifest.closure(app.id)]
    _, previous = release_mod.released_bom(manifest, app)

    if args.dry_run:
        print(f"== dry-run: {app.id} {app.version} -> {new_version} ==")
        print("Fecho: " + ", ".join(closure))
        print("Nada e testado, bumpado, gravado nem tagueado.\n")
        with tempfile.TemporaryDirectory() as tmp:
            bom = release_mod.build_app(manifest, app, Path(tmp) / app.id)
        print()
        release_mod.report_release(previous, bom)
        print(f"\nTag que o release.yml criaria: {app.id}@{new_version}")
        return 0

    print(f"== 1/4  Provando o fecho: testes de {len(closure)} unidades e a suite central ==")
    if _run_tests(manifest, _targets_for(manifest, closure, global_change=True), ["-q"]) != 0:
        return 1
    print("\n== 2/4  Versoes e fronteiras ==")
    if _check_versions(manifest) != 0 or _lint_imports(manifest) != 0:
        return 1
    print("\n== 3/4  Subindo a versao do app ==")
    release_mod.bump(manifest, app.id, args.part)
    # Antes do BOM: ele guarda o sha256 do uv.lock, e o lock registra a versao do app.
    if release_mod.refresh_lock(root) != 0:
        return 1
    manifest = _manifest(root)
    app = manifest.find(app.id)
    print("\n== 4/4  BOM do release ==")
    bom = release_mod.build_app(manifest, app)
    release_mod.report_release(previous, bom)
    target = release_mod.write_release(manifest, app, bom)
    print(
        f"\nGravado {target.relative_to(root).as_posix()}. Abra o PR com ele, com o bump e com o uv.lock."
    )
    print(
        f"Quando entrar na main, o release.yml confere o BOM e cria a tag {release_mod.release_tag(bom)}."
    )
    return 0


def cmd_verify_release(args: argparse.Namespace, root: Path) -> int:
    """Confere `.releases/<app>.json` contra o codigo de agora. E o que o release.yml roda."""
    manifest = _manifest(root)
    try:
        app = manifest.find(args.app)
    except KeyError as exc:
        print(exc, file=sys.stderr)
        return 1
    try:
        problems = release_mod.verify_release(manifest, app)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if problems:
        print(f"O BOM de {app.id} nao bate com o codigo:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    _, bom = release_mod.released_bom(manifest, app)
    assert bom is not None
    print(f"BOM de {app.id} confere com o codigo. Tag: {release_mod.release_tag(bom)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """O parser de linha de comando, com um subcomando por tarefa."""
    parser = argparse.ArgumentParser(
        prog="dev", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="manifesto, gerados, versoes, import-linter e mypy")
    p.add_argument(
        "--no-mypy",
        action="store_true",
        help="pula o mypy (o hook de pre-commit roda ele so no push)",
    )
    p.set_defaults(func=cmd_check)

    sub.add_parser("gen", help="regenera .importlinter e CODEOWNERS").set_defaults(func=cmd_gen)
    sub.add_parser("lint-imports", help="so o import-linter").set_defaults(func=cmd_lint_imports)

    p = sub.add_parser("affected", help="unidades afetadas pela branch")
    p.add_argument("--base", default="origin/main", help="ref de comparacao (padrao: origin/main)")
    p.add_argument("--json", action="store_true", help="saida em JSON, para o CI")
    p.add_argument("files", nargs="*", help="arquivos alterados (em vez de perguntar ao git)")
    p.set_defaults(func=cmd_affected)

    p = sub.add_parser("test", help="testes (todos, ou os afetados)")
    p.add_argument("--affected", action="store_true", help="so as unidades afetadas")
    p.add_argument("--base", default="origin/main", help="ref de comparacao (padrao: origin/main)")
    p.add_argument(
        "pytest_args", nargs="*", help="repassados ao pytest (opcoes desconhecidas tambem)"
    )
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("new", help="cria unidade a partir de tooling/templates/")
    p.add_argument(
        "kind", choices=["platform", "integration", "capability", "domain", "product", "app"]
    )
    p.add_argument("id", help="id em kebab-case; app aceita <produto>/<app>")
    p.add_argument("--depends-on", nargs="*", default=[], help="ids das unidades de que depende")
    p.add_argument("--product", help="produto dono (obrigatorio em app e product)")
    p.add_argument(
        "--runtime", choices=list(APP_RUNTIMES), help="so app: o modelo (padrao: fastapi-api)"
    )
    p.add_argument("--lifecycle", default="pilot", choices=["production", "pilot", "prototype"])
    p.add_argument("--description", help="uma frase sobre o que a unidade faz")
    p.add_argument("--dry-run", action="store_true", help="mostra o que criaria, sem escrever nada")
    p.set_defaults(func=cmd_new)

    sub.add_parser("version", help="versao de cada unidade").set_defaults(func=cmd_version)

    p = sub.add_parser("bump", help="sobe a versao de UMA unidade")
    p.add_argument("unit")
    p.add_argument("part", help="patch | minor | major | X.Y.Z")
    p.set_defaults(func=cmd_bump)

    p = sub.add_parser("build", help="app: BOM do fecho em dist/<app>/; unidade: wheel em dist/")
    p.add_argument("units", nargs="*")
    p.add_argument(
        "--all-apps", action="store_true", help="o fecho de cada app Python do manifesto (o CI usa)"
    )
    p.add_argument("--image", action="store_true", help="so app: monta tambem a imagem Docker")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("release", help="testa o fecho, sobe o app e grava o BOM")
    p.add_argument("app")
    p.add_argument("part", help="patch | minor | major | X.Y.Z")
    p.add_argument(
        "--dry-run", action="store_true", help="so mostra o fecho, o BOM e o que mudaria"
    )
    p.set_defaults(func=cmd_release)

    p = sub.add_parser("verify-release", help="confere o BOM gravado contra o codigo")
    p.add_argument("app")
    p.set_defaults(func=cmd_verify_release)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Despacha o subcomando e devolve o codigo de saida."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
    args, unknown = parser.parse_known_args(raw)
    if args.command == "test":
        # Tudo o que o `test` nao conhece vai para o pytest, NA ORDEM em que veio: o argparse
        # separa posicionais de opcoes, e `-p no:cacheprovider` virava `no:cacheprovider -p`.
        args.pytest_args = _pytest_args(raw[raw.index("test") + 1 :])
    elif unknown:
        parser.error(f"argumentos desconhecidos: {' '.join(unknown)}")
    return int(args.func(args, find_root()))


def _pytest_args(after_test: list[str]) -> list[str]:
    """Os argumentos depois de `test`, sem as opcoes do proprio `dev test`."""
    out: list[str] = []
    skip_next = False
    for item in after_test:
        if skip_next:
            skip_next = False
        elif item == "--affected" or item.startswith("--base="):
            continue
        elif item == "--base":
            skip_next = True
        else:
            out.append(item)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
