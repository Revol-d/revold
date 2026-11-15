"""Manifesto do monorepo: os `unit.yaml` de cada unidade (ADR-0030).

Le, valida e expoe as unidades. Tudo o que o tooling gera (`.importlinter`, CODEOWNERS,
grafo de afetados) parte daqui, e nada disso e editado a mao.
"""

from __future__ import annotations

import json
import keyword
import re
import tomllib
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import jsonschema
import yaml

UNIT_FILE = "unit.yaml"
SCHEMA_FILE = Path("tooling") / "schema" / "unit.schema.json"
REPO_CONFIG_FILE = Path("tooling") / "repo.yaml"

# Prefixo do pacote importavel e da distribuicao das libs e do produto. App fica sem prefixo.
PACKAGE_PREFIX = "revold"

LIB_KINDS = frozenset({"platform", "integration", "capability", "domain"})
LAYERED_KINDS = frozenset({"domain", "product"})

# Regra de dependencia (D1), por tipo: de quem cada tipo pode depender diretamente.
# `domain -> integration` e permitido no manifesto, mas o import fica restrito a camada
# `adapters/` (o .importlinter gerado fiscaliza). Ver docs/ARQUITETURA.md, secao 3.
ALLOWED_DEPENDENCY_KINDS: dict[str, frozenset[str]] = {
    "platform": frozenset({"platform"}),
    "integration": frozenset({"platform"}),
    "capability": frozenset({"platform", "capability"}),
    "domain": frozenset({"platform", "capability", "integration"}),
    "product": frozenset({"platform", "capability", "integration", "domain"}),
    "app": frozenset({"platform", "capability", "integration", "domain", "product"}),
    "web": frozenset({"web"}),
}

# Unidade TypeScript (a lib web e os sites) so depende de `web`: um site nao importa pacote
# Python. O resto fala com ele por HTTP, e o contrato (OpenAPI) nao e dependencia de build.
TYPESCRIPT_DEPENDENCY_KINDS = frozenset({"web"})
TYPESCRIPT_RUNTIMES = frozenset({"next-web"})

# Pastas que nunca guardam `unit.yaml` de unidade: ambiente, cache e os modelos do `dev new`.
_SKIPPED_PARTS = frozenset(
    {"src", "tests", "node_modules", ".venv", "__pycache__", "templates", ".next"}
)


class ManifestError(Exception):
    """O manifesto nao passou na validacao. A mensagem lista todos os problemas."""

    def __init__(self, problems: list[str]) -> None:
        """Guarda a lista de problemas para quem quiser trata-los um a um."""
        self.problems = problems
        super().__init__("Manifesto invalido:\n" + "\n".join(f"  - {p}" for p in problems))


def normalize_distribution(name: str) -> str:
    """Nome de distribuicao normalizado (PEP 503): `revold_store_settings` -> `revold-store-settings`."""
    return re.sub(r"[-_.]+", "-", name).lower()


def import_name_for(unit_id: str, kind: str) -> str:
    """Nome de import de uma unidade NOVA: `revold_<id>` em libs e produto; `<id>` em app."""
    base = unit_id.replace("-", "_")
    return base if kind == "app" else f"{PACKAGE_PREFIX}_{base}"


def distribution_name_for(unit_id: str, kind: str) -> str:
    """Nome de distribuicao de uma unidade NOVA: `revold-<id>` em libs e produto; `<id>` em app."""
    return unit_id if kind == "app" else f"{PACKAGE_PREFIX}-{unit_id}"


def require_identifier(unit_id: str) -> None:
    """Recusa um id que nao vira `import` valido, ANTES de qualquer arquivo ser escrito.

    Um nome que nao e identificador Python gera um pacote que so quebra no primeiro `import`,
    longe da causa. `isidentifier()` sozinho nao basta, porque palavra reservada (`class`)
    tambem passa nele.
    """
    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", unit_id):
        raise ValueError(
            f"id invalido: {unit_id!r}. Use kebab-case: letras minusculas, digitos e hifen, comecando por letra."
        )
    for part in unit_id.split("-"):
        if keyword.iskeyword(part):
            raise ValueError(f"id invalido: {unit_id!r}. {part!r} e palavra reservada do Python.")


@dataclass(frozen=True)
class RepoConfig:
    """O `tooling/repo.yaml`."""

    unit_roots: tuple[str, ...]
    default_owners: tuple[str, ...]
    platform_owners: tuple[str, ...]
    platform_paths: tuple[str, ...]
    affected_global: tuple[str, ...]
    affected_paths: dict[str, tuple[str, ...]]

    @classmethod
    def load(cls, root: Path) -> RepoConfig:
        """Le o `tooling/repo.yaml` da raiz do repositorio."""
        data = yaml.safe_load((root / REPO_CONFIG_FILE).read_text(encoding="utf-8"))
        affected = data.get("affected") or {}
        return cls(
            unit_roots=tuple(data["unit_roots"]),
            default_owners=tuple(data["default_owners"]),
            platform_owners=tuple(data["platform_owners"]),
            platform_paths=tuple(data["platform_paths"]),
            affected_global=tuple(affected.get("global") or ()),
            affected_paths={k: tuple(v) for k, v in (affected.get("paths") or {}).items()},
        )


@dataclass(frozen=True)
class Unit:
    """Uma unidade do monorepo, como declarada no `unit.yaml`."""

    id: str
    kind: str
    product: str | None
    language: str
    lifecycle: str
    owners: tuple[str, ...]
    depends_on: tuple[str, ...]
    runtime: str | None
    tables_owned: tuple[str, ...]
    root: Path = field(repr=False, compare=False)
    pure_modules: tuple[str, ...] = ()
    stages: tuple[str, ...] = ()
    rel_dir: str = ""

    @property
    def directory(self) -> Path:
        """Pasta da unidade (absoluta)."""
        return self.root / self.rel_dir

    @property
    def is_python(self) -> bool:
        """Unidade Python, empacotada por `pyproject.toml`."""
        return self.language == "python"

    @property
    def is_layered(self) -> bool:
        """Unidade com camadas fiscalizadas por dentro (dominios e produto).

        Unidade `deprecated` fica de fora: e codigo em aposentadoria, que so carrega a regra de
        dependencia ate sumir.
        """
        return self.kind in LAYERED_KINDS and self.lifecycle != "deprecated"

    @cached_property
    def pyproject(self) -> dict[str, Any]:
        """O `pyproject.toml` da unidade, ou vazio se nao houver."""
        path = self.directory / "pyproject.toml"
        return tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    @property
    def distribution(self) -> str:
        """Nome de distribuicao normalizado, lido do `pyproject.toml`."""
        return normalize_distribution(self.pyproject.get("project", {}).get("name", ""))

    @property
    def version(self) -> str:
        """Versao declarada no `pyproject.toml`."""
        return str(self.pyproject.get("project", {}).get("version", ""))

    @cached_property
    def import_name(self) -> str:
        """O pacote importavel: a unica pasta com `__init__.py` dentro de `src/`."""
        packages = sorted(p.parent.name for p in (self.directory / "src").glob("*/__init__.py"))
        return packages[0] if len(packages) == 1 else ""

    @property
    def src_dir(self) -> Path:
        """A pasta `src/` da unidade."""
        return self.directory / "src"

    def top_level_modules(self) -> tuple[str, ...]:
        """Submodulos de primeiro nivel do pacote (subpacote ou `.py`), sem `__init__`."""
        if not self.import_name:
            return ()
        package = self.src_dir / self.import_name
        names = {p.parent.name for p in package.glob("*/__init__.py")}
        names |= {p.stem for p in package.glob("*.py") if p.stem != "__init__"}
        return tuple(sorted(names))

    def declared_requirements(self) -> set[str]:
        """Distribuicoes que o `pyproject.toml` pede, obrigatorias e extras, normalizadas."""
        project = self.pyproject.get("project", {})
        requirements = list(project.get("dependencies", []))
        for extra in (project.get("optional-dependencies") or {}).values():
            requirements.extend(extra)
        return {
            normalize_distribution(re.split(r"[\s<>=!~;\[]", r, maxsplit=1)[0])
            for r in requirements
        }


@dataclass(frozen=True)
class Manifest:
    """Todas as unidades do repositorio, ja validadas."""

    root: Path
    config: RepoConfig
    units: tuple[Unit, ...]

    @property
    def by_id(self) -> dict[str, Unit]:
        """Unidades indexadas pelo id."""
        return {u.id: u for u in self.units}

    @property
    def python_units(self) -> list[Unit]:
        """Unidades Python, na ordem do caminho."""
        return [u for u in self.units if u.is_python]

    def consumers(self) -> dict[str, set[str]]:
        """Para cada unidade, quem depende DIRETAMENTE dela."""
        reverse: dict[str, set[str]] = {u.id: set() for u in self.units}
        for unit in self.units:
            for dep in unit.depends_on:
                reverse.setdefault(dep, set()).add(unit.id)
        return reverse

    def closure(self, unit_id: str) -> list[Unit]:
        """A unidade e tudo de que ela depende, transitivamente, com as dependencias PRIMEIRO.

        E a ordem de instalacao: quem vem antes nunca importa quem vem depois. A ordem entre
        irmas e alfabetica, para o BOM sair igual em toda maquina.
        """
        by_id = self.by_id
        ordered: list[Unit] = []
        seen: set[str] = set()

        def visit(current: str) -> None:
            if current in seen:
                return
            seen.add(current)
            for dep in sorted(by_id[current].depends_on):
                visit(dep)
            ordered.append(by_id[current])

        visit(unit_id)
        return ordered

    def find(self, name: str) -> Unit:
        """Unidade pelo id, pelo nome da pasta ou pelo nome de distribuicao."""
        wanted = normalize_distribution(name)
        for unit in self.units:
            if name in (unit.id, unit.directory.name) or (
                unit.distribution and wanted == unit.distribution
            ):
                return unit
        known = ", ".join(sorted(u.id for u in self.units))
        raise KeyError(f"Unidade desconhecida: {name!r}. Conhecidas: {known}")


def find_unit_files(root: Path, config: RepoConfig) -> list[Path]:
    """Todos os `unit.yaml` de unidade, em ordem de caminho."""
    found = []
    for base in config.unit_roots:
        base_dir = root / base
        if not base_dir.is_dir():
            continue
        for path in base_dir.rglob(UNIT_FILE):
            if not _SKIPPED_PARTS.intersection(path.relative_to(root).parts[:-1]):
                found.append(path)
    return sorted(found)


def load_manifest(root: Path) -> Manifest:
    """Le e valida o manifesto. Levanta `ManifestError` com TODOS os problemas de uma vez."""
    config = RepoConfig.load(root)
    schema = json.loads((root / SCHEMA_FILE).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    problems: list[str] = []
    units: list[Unit] = []
    for path in find_unit_files(root, config):
        rel = path.relative_to(root).as_posix()
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            problems.append(f"{rel}: YAML invalido ({exc})")
            continue
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if errors:
            problems.extend(
                f"{rel}: {'.'.join(map(str, e.absolute_path)) or '(raiz)'}: {e.message}"
                for e in errors
            )
            continue
        units.append(
            Unit(
                id=data["id"],
                kind=data["kind"],
                product=data.get("product") or None,
                language=data["language"],
                lifecycle=data["lifecycle"],
                owners=tuple(data["owners"]),
                depends_on=tuple(data["depends_on"]),
                runtime=data.get("runtime"),
                tables_owned=tuple((data.get("data") or {}).get("tables_owned") or ()),
                pure_modules=tuple(data.get("pure_modules") or ()),
                stages=tuple(data.get("stages") or ()),
                root=root,
                rel_dir=path.parent.relative_to(root).as_posix(),
            )
        )

    manifest = Manifest(root=root, config=config, units=tuple(units))
    problems.extend(validate(manifest))
    if problems:
        raise ManifestError(problems)
    return manifest


def validate(manifest: Manifest) -> list[str]:
    """Regras que o schema nao alcanca: ids, grafo, D1, ciclo de vida e empacotamento."""
    problems: list[str] = []
    seen: dict[str, str] = {}
    for unit in manifest.units:
        if unit.id in seen:
            problems.append(f"id repetido {unit.id!r}: {seen[unit.id]} e {unit.rel_dir}")
        seen[unit.id] = unit.rel_dir

    by_id = manifest.by_id
    for unit in manifest.units:
        problems.extend(_validate_unit_fields(unit))
        for dep_id in unit.depends_on:
            dep = by_id.get(dep_id)
            if dep is None:
                problems.append(f"{unit.id}: depends_on cita {dep_id!r}, que nao existe")
                continue
            if dep_id == unit.id:
                problems.append(f"{unit.id}: depende de si mesma")
                continue
            typescript = unit.language == "typescript"
            allowed = (
                TYPESCRIPT_DEPENDENCY_KINDS if typescript else ALLOWED_DEPENDENCY_KINDS[unit.kind]
            )
            if dep.kind not in allowed:
                label = f"{unit.kind}, typescript" if typescript else unit.kind
                problems.append(
                    f"{unit.id} ({label}) nao pode depender de {dep.id} ({dep.kind}) pela regra D1"
                )
            if unit.lifecycle == "production" and dep.lifecycle == "prototype":
                problems.append(f"{unit.id} e production e depende de {dep.id}, que e prototype")
        if unit.is_python:
            problems.extend(_validate_python_unit(unit, manifest))
        if unit.pure_modules and unit.is_python and unit.import_name:
            missing = sorted(set(unit.pure_modules) - set(unit.top_level_modules()))
            if missing:
                problems.append(
                    f"{unit.id}: pure_modules cita {missing}, que nao existem em {unit.import_name}"
                )
        if unit.stages and unit.is_python and unit.import_name:
            application = unit.src_dir / unit.import_name / "application"
            names = [name.strip() for line in unit.stages for name in line.split("|")]
            missing = sorted(n for n in names if not (application / n / "__init__.py").is_file())
            if missing:
                problems.append(
                    f"{unit.id}: stages cita {missing}, que nao existem em {unit.import_name}.application"
                )

    cycle = _find_cycle(manifest)
    if cycle:
        problems.append("ciclo de dependencia: " + " -> ".join(cycle))
    problems.extend(_validate_workspace_sources(manifest))
    return problems


def _validate_unit_fields(unit: Unit) -> list[str]:
    problems = []
    if unit.kind == "app" and not unit.runtime:
        problems.append(f"{unit.id}: app precisa de `runtime`")
    if unit.kind != "app" and unit.runtime:
        problems.append(f"{unit.id}: `runtime` so vale em app")
    if unit.kind in {"app", "product"} and not unit.product:
        problems.append(f"{unit.id}: {unit.kind} precisa de `product`")
    if unit.kind in LIB_KINDS and unit.product:
        problems.append(f"{unit.id}: unidade de libs/ nao tem `product`")
    if unit.stages and unit.kind not in LAYERED_KINDS:
        problems.append(f"{unit.id}: `stages` so vale em domain e product")
    if unit.pure_modules and unit.kind != "integration":
        problems.append(f"{unit.id}: `pure_modules` so vale em integration")
    typescript = unit.kind == "web" or unit.runtime in TYPESCRIPT_RUNTIMES
    if typescript != (unit.language == "typescript"):
        problems.append(
            f"{unit.id}: language {unit.language} nao combina com kind {unit.kind}/runtime {unit.runtime}"
        )
    return problems


def _validate_python_unit(unit: Unit, manifest: Manifest) -> list[str]:
    """O `pyproject.toml` e o pacote em `src/` batem com o manifesto."""
    if not unit.pyproject:
        return [f"{unit.id}: unidade Python sem pyproject.toml em {unit.rel_dir}"]
    problems = []
    if not unit.import_name:
        problems.append(f"{unit.id}: esperado exatamente um pacote em {unit.rel_dir}/src/")
    internal = {u.distribution: u.id for u in manifest.python_units}
    required = {internal[d] for d in unit.declared_requirements() if d in internal}
    declared = set(unit.depends_on)
    if missing := sorted(required - declared):
        problems.append(f"{unit.id}: o pyproject.toml pede {missing}, que faltam no depends_on")
    python_deps = {d for d in declared if d in manifest.by_id and manifest.by_id[d].is_python}
    if extra := sorted(python_deps - required):
        problems.append(f"{unit.id}: depends_on cita {extra}, que o pyproject.toml nao pede")
    return problems


def _validate_workspace_sources(manifest: Manifest) -> list[str]:
    """Toda unidade Python resolve do workspace, nunca do PyPI (protecao contra dependency confusion)."""
    root_pyproject = tomllib.loads((manifest.root / "pyproject.toml").read_text(encoding="utf-8"))
    declared = root_pyproject.get("tool", {}).get("uv", {}).get("sources", {})
    sources = {normalize_distribution(k): v for k, v in declared.items()}
    problems = []
    for unit in manifest.python_units:
        if unit.kind == "app":
            continue
        if not (sources.get(unit.distribution) or {}).get("workspace"):
            problems.append(
                f"{unit.id}: {unit.distribution} falta em [tool.uv.sources] da raiz com workspace = true"
            )
    return problems


def _find_cycle(manifest: Manifest) -> list[str]:
    """Um ciclo do grafo de dependencias, se houver (busca em profundidade)."""
    by_id = manifest.by_id
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str]:
        state[node] = 1
        stack.append(node)
        for dep in by_id[node].depends_on if node in by_id else ():
            if state.get(dep) == 1:
                return stack[stack.index(dep) :] + [dep]
            if dep in by_id and not state.get(dep):
                found = visit(dep)
                if found:
                    return found
        stack.pop()
        state[node] = 2
        return []

    for unit_id in sorted(by_id):
        if not state.get(unit_id):
            found = visit(unit_id)
            if found:
                return found
    return []
