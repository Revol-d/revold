"""Versao, fecho, BOM e release (ADR-0029).

O versionamento e INDEPENDENTE por unidade, nunca lockstep: `bump` mexe em UM pyproject.toml
so. O app so muda de versao no `release`, e so depois de os testes passarem. Ver
docs/versionamento-e-deploy.md.

O deploy de um app e o FECHO dele (o app e tudo de que ele depende), descrito no BOM: para cada
unidade, a versao e o sha256 do `src/`; mais o sha256 do `uv.lock`, que trava os terceiros. O
numero sozinho nao prova conteudo: o BOM e o que diz que a imagem publicada com a tag
`<app>@<versao>` saiu exatamente do codigo que o PR de release aprovou.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from revold_tooling.manifest import Manifest, Unit, normalize_distribution

# `version = "X.Y.Z"` na PRIMEIRA ocorrencia (o bloco [project]); um `version` que apareca
# depois (em [tool.*]) nao e o do pacote e nao pode ser reescrito.
_VERSION_RE = re.compile(
    r'^(?P<before>version\s*=\s*")(?P<version>[^"]+)(?P<after>")', re.MULTILINE
)
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

BOM_SCHEMA = 1
RELEASES_DIR = ".releases"
LOCK_FILE = "uv.lock"
IMAGE_NAMESPACE = "revold"

# O que nunca entra no sha256 de um `src/`: cache do interpretador.
_IGNORED_PARTS = frozenset({"__pycache__"})
_IGNORED_SUFFIXES = frozenset({".pyc", ".pyo"})


def next_version(current: str, part: str) -> str:
    """A versao seguinte: `patch`, `minor`, `major` ou uma `X.Y.Z` explicita."""
    if _SEMVER_RE.match(part):
        return part
    if not _SEMVER_RE.match(current):
        raise ValueError(f"Versao atual {current!r} nao e X.Y.Z; informe uma explicita, ex.: 1.2.3")
    major, minor, patch = (int(x) for x in current.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Parte invalida: {part!r}. Use patch | minor | major | X.Y.Z")


def set_version(pyproject: Path, new_version: str) -> None:
    """Reescreve so o `version` do bloco [project]."""
    content = pyproject.read_text(encoding="utf-8")
    updated, n = _VERSION_RE.subn(rf"\g<before>{new_version}\g<after>", content, count=1)
    if not n:
        raise ValueError(f"Nao consegui reescrever a versao em {pyproject}")
    pyproject.write_text(updated, encoding="utf-8", newline="")


def print_versions(manifest: Manifest) -> None:
    """Versao de cada unidade Python."""
    for unit in manifest.python_units:
        print(f"  {unit.version:10s} {unit.id:28s} {unit.rel_dir}")


def bump(manifest: Manifest, name: str, part: str) -> str:
    """Sobe a versao de UMA unidade e devolve a nova. Nenhuma outra e tocada."""
    unit = manifest.find(name)
    if not unit.is_python:
        raise ValueError(
            f"{unit.id} e TypeScript: a versao dela mora no package.json e nao passa por aqui."
        )
    current = unit.version
    new = next_version(current, part)
    if new == current:
        print(f"{unit.id} ja esta em {current}; nada a fazer.")
        return current
    set_version(unit.directory / "pyproject.toml", new)
    print(f"{unit.id}: {current} -> {new}")
    print("Nenhuma outra unidade foi tocada (versionamento independente).")
    return new


def refresh_lock(root: Path) -> int:
    """Atualiza o `uv.lock` depois de uma mudanca de versao.

    O lock registra a versao de cada membro do workspace. Sem isto, o `bump` deixaria o lock
    velho: o proximo `uv sync` de qualquer pessoa o reescreveria, e o BOM de um release (que
    guarda o sha256 do lock) seria calculado sobre um arquivo que ainda ia mudar.
    """
    if not (root / LOCK_FILE).is_file():
        return 0
    uv = shutil.which("uv")
    if not uv:
        print("`uv` nao esta no PATH: rode `uv lock` antes de commitar.", file=sys.stderr)
        return 1
    return subprocess.call([uv, "lock", "-q"], cwd=root)


# --------------------------------------------------------------------- conteudo
def _normalized_bytes(path: Path) -> bytes:
    """Bytes do arquivo com fim de linha LF.

    O checkout do Windows (autocrlf) entrega CRLF e o runner do CI entrega LF. Sem normalizar,
    o mesmo commit teria um sha256 em cada maquina e o `release.yml` reprovaria todo BOM gerado
    num Windows.
    """
    return path.read_bytes().replace(b"\r\n", b"\n")


def sha256_of_file(path: Path) -> str:
    """sha256 de um arquivo de texto, com o fim de linha normalizado."""
    return hashlib.sha256(_normalized_bytes(path)).hexdigest()


def sha256_of_source(src_dir: Path) -> str:
    """sha256 de tudo o que esta em `src/`: os caminhos e o conteudo, em ordem estavel.

    O caminho entra na conta: mover um arquivo muda o que a imagem instala, mesmo sem mudar
    uma linha de conteudo.
    """
    digest = hashlib.sha256()
    files = sorted(
        p
        for p in src_dir.rglob("*")
        if p.is_file()
        and not _IGNORED_PARTS.intersection(p.parts)
        and p.suffix not in _IGNORED_SUFFIXES
    )
    for path in files:
        digest.update(path.relative_to(src_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_normalized_bytes(path))
        digest.update(b"\0")
    return digest.hexdigest()


# --------------------------------------------------------------------- BOM
@dataclass(frozen=True)
class BomEntry:
    """Uma unidade do fecho: qual, que versao e que conteudo."""

    unidade: str
    versao: str
    sha256: str


@dataclass(frozen=True)
class Bom:
    """O que um release de app leva, na ordem de instalacao.

    `lock_sha256` e o sha256 do `uv.lock` no momento do release: e ele que trava a versao de
    cada dependencia de terceiro que a imagem instala.
    """

    app: str
    versao: str
    unidades: tuple[BomEntry, ...]
    lock_sha256: str = ""
    schema: int = field(default=BOM_SCHEMA)

    def versions(self) -> dict[str, str]:
        """Distribuicao normalizada -> versao."""
        return {normalize_distribution(e.unidade): e.versao for e in self.unidades}

    def hashes(self) -> dict[str, str]:
        """Distribuicao normalizada -> sha256 do `src/`."""
        return {normalize_distribution(e.unidade): e.sha256 for e in self.unidades}

    def to_json(self) -> str:
        """Texto estavel: mesmo fecho, mesmo arquivo, byte a byte."""
        data = {
            "schema": self.schema,
            "app": self.app,
            "versao": self.versao,
            "lock_sha256": self.lock_sha256,
            "unidades": [asdict(e) for e in self.unidades],
        }
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Bom:
        """Le um BOM gravado por `to_json`."""
        data = json.loads(text)
        if data.get("schema") != BOM_SCHEMA:
            raise ValueError(
                f"BOM com schema {data.get('schema')!r}; este tooling le o schema {BOM_SCHEMA}"
            )
        return cls(
            app=data["app"],
            versao=data["versao"],
            unidades=tuple(BomEntry(**e) for e in data["unidades"]),
            lock_sha256=data.get("lock_sha256", ""),
        )


def bom_filename(app: Unit) -> str:
    """Nome do BOM dentro de `dist/<app>/`."""
    return f"{app.id}.bom.json"


def release_file(manifest: Manifest, app: Unit) -> Path:
    """O BOM versionado do ultimo release do app, em `.releases/<app>.json`."""
    return manifest.root / RELEASES_DIR / f"{app.id}.json"


def released_bom(manifest: Manifest, app: Unit) -> tuple[Path | None, Bom | None]:
    """O BOM do ultimo release do app e o arquivo de onde veio. Sem release: `(None, None)`."""
    path = release_file(manifest, app)
    if not path.is_file():
        return None, None
    return path, Bom.from_json(path.read_text(encoding="utf-8"))


def compute_bom(manifest: Manifest, app: Unit) -> Bom:
    """O BOM do fecho do app como o codigo esta agora."""
    if app.kind != "app":
        raise ValueError(f"{app.id!r} nao e um app; o fecho e de app.")
    if not app.is_python:
        raise ValueError(
            f"{app.id!r} e TypeScript: o fecho e o release pelo tooling so cobrem app Python."
        )
    entries = [
        BomEntry(
            unidade=unit.distribution, versao=unit.version, sha256=sha256_of_source(unit.src_dir)
        )
        for unit in manifest.closure(app.id)
        if unit.is_python
    ]
    lock = manifest.root / LOCK_FILE
    lock_sha256 = sha256_of_file(lock) if lock.is_file() else ""
    return Bom(app=app.id, versao=app.version, unidades=tuple(entries), lock_sha256=lock_sha256)


def image_tag(app: Unit) -> str:
    """A tag local da imagem do app: `revold/<app>:<versao>`."""
    return f"{IMAGE_NAMESPACE}/{app.id}:{app.version}"


# --------------------------------------------------------------------- build
def _uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("`uv` nao esta no PATH; o build de wheel usa `uv build`.")
    return uv


def build_app(
    manifest: Manifest, app: Unit, out_dir: Path | None = None, *, image: bool = False
) -> Bom:
    """Gera `dist/<app>/<app>.bom.json` e, com `image`, a imagem Docker do app.

    A imagem sai do `Dockerfile` da pasta do app, com o contexto na raiz do monorepo: o
    `uv sync --package` de dentro dela precisa do workspace inteiro.
    """
    bom = compute_bom(manifest, app)
    out = out_dir or manifest.root / "dist" / app.id
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / bom_filename(app)).write_text(bom.to_json(), encoding="utf-8", newline="")
    where = (
        out.relative_to(manifest.root).as_posix() if out.is_relative_to(manifest.root) else str(out)
    )
    print(f"\nFecho de {app.id}: {len(bom.unidades)} unidade(s). {bom_filename(app)} em {where}.")

    if image:
        dockerfile = app.directory / "Dockerfile"
        if not dockerfile.is_file():
            raise SystemExit(
                f"{app.id} nao tem Dockerfile em {app.rel_dir}; nao ha imagem para montar."
            )
        docker = shutil.which("docker")
        if not docker:
            raise SystemExit("`docker` nao esta no PATH; sem ele a imagem nao e montada.")
        rel_dockerfile = dockerfile.relative_to(manifest.root).as_posix()
        run(
            [
                docker,
                "build",
                "--target",
                "runtime",
                "-f",
                rel_dockerfile,
                "-t",
                image_tag(app),
                ".",
            ],
            manifest.root,
        )
        print(f"Imagem {image_tag(app)} montada.")
    return bom


def build(manifest: Manifest, names: list[str]) -> list[Unit]:
    """Wheel de cada unidade pedida (ou de todas as libs e do produto) em `dist/`, sem BOM."""
    units = (
        [manifest.find(n) for n in names]
        if names
        else [u for u in manifest.python_units if u.kind != "app"]
    )
    dist = manifest.root / "dist"
    dist.mkdir(exist_ok=True)
    built = []
    for unit in units:
        if "build-system" not in unit.pyproject:
            print(f"  {unit.id}: sem [build-system], nao vira wheel")
            continue
        for old in dist.glob(f"{unit.distribution.replace('-', '_')}-*.whl"):
            old.unlink()
        run(
            [_uv(), "build", "--package", unit.distribution, "--wheel", "-o", str(dist), "-q"],
            manifest.root,
        )
        built.append(unit)
    print(f"\n{len(built)} wheel(s) em dist/.")
    return built


def run(cmd: list[str], cwd: Path) -> None:
    """Executa um comando e aborta o processo com o codigo dele se falhar."""
    print(f"$ {' '.join(cmd)}", flush=True)
    code = subprocess.call(cmd, cwd=cwd)
    if code != 0:
        print(f"\nFALHOU (codigo {code}): {' '.join(cmd)}", file=sys.stderr)
        raise SystemExit(code)


# --------------------------------------------------------------------- release
def report_release(previous: Bom | None, bom: Bom) -> list[str]:
    """Diz o que mudou desde o ultimo release e devolve as unidades que mudaram de versao."""
    current = bom.versions()
    before = previous.versions() if previous else {}
    changed = sorted(n for n, v in current.items() if before.get(n) != v)
    if previous is None:
        print("Primeiro release deste app: nao ha o que comparar.")
    elif changed:
        print("Mudou de versao desde o ultimo release deste app:")
        for name in changed:
            print(f"  {name} {before.get(name, '(nova)')} -> {current[name]}")
    else:
        print("Nada mudou desde o ultimo release. (Estranho num release: conferir se bumpou algo.)")
    if previous is not None and previous.lock_sha256 != bom.lock_sha256:
        print(
            "O uv.lock mudou desde o ultimo release: confira no diff quais terceiros mudaram de versao."
        )
    return changed


def write_release(manifest: Manifest, app: Unit, bom: Bom) -> Path:
    """Grava `.releases/<app>.json`."""
    target = release_file(manifest, app)
    target.parent.mkdir(exist_ok=True)
    target.write_text(bom.to_json(), encoding="utf-8", newline="")
    return target


def verify_release(manifest: Manifest, app: Unit) -> list[str]:
    """Confere o BOM versionado do app contra o codigo de agora. Devolve as divergencias.

    E o que o `release.yml` roda na `main` antes de criar a tag: se o codigo que entrou nao e o
    que o BOM descreve, o release para.
    """
    path, recorded = released_bom(manifest, app)
    if recorded is None or path is None:
        return [f"{app.id}: nao ha `.releases/{app.id}.json` para conferir"]
    current = compute_bom(manifest, app)
    problems = []
    if recorded.versao != current.versao:
        problems.append(
            f"{app.id}: o BOM diz {recorded.versao} e o pyproject.toml diz {current.versao}"
        )
    recorded_units = {normalize_distribution(e.unidade): e for e in recorded.unidades}
    current_units = {normalize_distribution(e.unidade): e for e in current.unidades}
    for name in sorted(set(recorded_units) | set(current_units)):
        old, new = recorded_units.get(name), current_units.get(name)
        if old is None:
            problems.append(f"{name}: esta no fecho e nao esta no BOM")
        elif new is None:
            problems.append(f"{name}: esta no BOM e saiu do fecho")
        elif old.versao != new.versao:
            problems.append(f"{name}: o BOM diz {old.versao} e o codigo diz {new.versao}")
        elif old.sha256 != new.sha256:
            problems.append(f"{name} {new.versao}: o conteudo do src/ nao e o que o BOM aprovou")
    if recorded.lock_sha256 != current.lock_sha256:
        problems.append("uv.lock: nao e o que o BOM aprovou")
    return problems


def release_tag(bom: Bom) -> str:
    """A tag do release: `<app>@<versao>` (ADR-0028)."""
    return f"{bom.app}@{bom.versao}"
