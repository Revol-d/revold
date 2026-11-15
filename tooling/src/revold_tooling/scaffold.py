"""`dev new`: cria uma unidade a partir de `tooling/templates/`.

A regra mais cara de aprender: **o tool nao pode mentir que deu certo**. Por isso o id e
validado antes de qualquer escrita, o codigo gerado e compilado e o manifesto inteiro e
revalidado; se algo falhar, a pasta criada e apagada e o `pyproject.toml` da raiz volta como
estava.

Tres modelos: `python-lib` para as libs e o produto, e um por runtime de app Python
(`fastapi-api` e `celery-worker`). Todos sao arquivos `.tmpl` com `{{chave}}`. Site novo
(`next-web`) ainda nao tem modelo: copie um dos sites existentes e escreva o `unit.yaml`.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from revold_tooling.generate import write_generated
from revold_tooling.manifest import (
    ManifestError,
    RepoConfig,
    distribution_name_for,
    import_name_for,
    load_manifest,
    require_identifier,
)

TEMPLATES_DIR = Path("tooling") / "templates"

# Onde cada tipo mora. `platform` e um pacote so, entao nao leva o id no caminho.
_LOCATION = {
    "platform": "libs/platform",
    "integration": "libs/integrations/{id}",
    "capability": "libs/capabilities/{id}",
    "domain": "libs/domains/{id}",
    "product": "products/{id}",
    "app": "apps/{product}/{id}",
}

APP_RUNTIMES = ("fastapi-api", "celery-worker")
DEFAULT_APP_RUNTIME = "fastapi-api"
# A dependencia que cada runtime usa no codigo que o modelo gera: o settings dos apps Python le
# o ambiente pelo `revold_platform.configuration`.
_RUNTIME_REQUIRES = {"fastapi-api": "platform", "celery-worker": "platform"}

# Camadas criadas vazias em dominio e produto. O .importlinter gerado fiscaliza a ordem.
_LAYERS = {
    "domain": {
        "domain": "Regras e modelos do dominio. Nao importa adapters nem cliente de integracao.",
        "application": "Casos de uso do dominio. Nao importa adapters nem cliente de integracao.",
        "ports": "Contratos (Protocols) que os adapters implementam.",
        "adapters": "Implementacoes das portas. Unica camada que importa integracao ou biblioteca de I/O.",
        "adapters/memory": "Adapters em memoria, para teste e para o modo local do app (nunca `testing/`).",
    },
    "product": {
        "domain": "Regras e modelos do produto. Nao importa adapters nem cliente de integracao.",
        "application": "Casos de uso do produto: o que cruza dois ou mais dominios.",
        "ports": "So as portas do produto; as de cada contexto moram nos dominios de libs/.",
        "adapters": "Implementacoes das portas do produto.",
    },
}


@dataclass(frozen=True)
class NewUnit:
    """Pedido de criacao de uma unidade."""

    kind: str
    id: str
    depends_on: tuple[str, ...] = ()
    product: str | None = None
    lifecycle: str = "pilot"
    description: str = ""
    owners: tuple[str, ...] = ()
    runtime: str | None = None


@dataclass(frozen=True)
class Created:
    """O que o `dev new` criou (ou criaria, no dry-run)."""

    target: Path
    files: tuple[str, ...]
    added_dependencies: tuple[str, ...]
    root_changes: tuple[str, ...]


def normalize_request(request: NewUnit) -> NewUnit:
    """Aceita `app <produto>/<app>` e preenche o runtime padrao do app."""
    if request.kind == "app" and "/" in request.id:
        product, _, app_id = request.id.partition("/")
        if request.product and request.product != product:
            raise ValueError(
                f"--product {request.product!r} contradiz o {product!r} de {request.id!r}"
            )
        request = replace(request, id=app_id, product=product)
    if request.kind == "app":
        runtime = request.runtime or DEFAULT_APP_RUNTIME
        if runtime not in APP_RUNTIMES:
            raise ValueError(
                f"runtime {runtime!r} nao tem modelo. Runtimes: {', '.join(APP_RUNTIMES)}"
            )
        request = replace(request, runtime=runtime)
    elif request.runtime:
        raise ValueError("--runtime so vale para app")
    return request


def create_unit(root: Path, request: NewUnit, dry_run: bool = False) -> Created:
    """Cria a unidade (ou so mostra, no dry-run). Levanta `ValueError` sem deixar nada pela metade."""
    request = normalize_request(request)
    require_identifier(request.id)
    if request.product:
        require_identifier(request.product)
    if request.kind not in _LOCATION:
        raise ValueError(
            f"tipo {request.kind!r} nao tem modelo. Tipos: {', '.join(sorted(_LOCATION))}"
        )
    if request.kind in {"app", "product"} and not request.product:
        raise ValueError(f"{request.kind} precisa de --product (ou `app <produto>/<app>`)")
    if request.kind == "platform" and request.id != "platform":
        raise ValueError("so existe uma unidade platform, com id `platform`")

    manifest = load_manifest(root)
    by_id = manifest.by_id
    if request.id in by_id:
        raise ValueError(f"ja existe a unidade {request.id!r} em {by_id[request.id].rel_dir}")
    added: tuple[str, ...] = ()
    required = _RUNTIME_REQUIRES.get(request.runtime or "")
    if required and required not in request.depends_on:
        request = replace(request, depends_on=(required, *request.depends_on))
        added = (required,)
    unknown = [d for d in request.depends_on if d not in by_id]
    if unknown:
        raise ValueError(f"depends_on cita unidades que nao existem: {unknown}")

    rel_dir = _LOCATION[request.kind].format(id=request.id, product=request.product)
    target = root / rel_dir
    if target.exists():
        raise ValueError(f"a pasta {rel_dir} ja existe")

    template = request.runtime if request.kind == "app" else "python-lib"
    assert template is not None
    values = _template_values(request, manifest.by_id, RepoConfig.load(root), rel_dir)
    root_changes = []
    if request.kind == "app":
        root_changes.append(f'pyproject.toml: "{rel_dir}" em [tool.uv.workspace].members')
    else:
        root_changes.append(
            f"pyproject.toml: {values['dist']} = {{ workspace = true }} em [tool.uv.sources]"
        )
    root_changes.append(".importlinter e .github/CODEOWNERS regenerados")

    if dry_run:
        with tempfile.TemporaryDirectory() as tmp:
            preview = Path(tmp) / "unit"
            _render_unit(root / TEMPLATES_DIR / template, preview, request, values)
            files = _listing(preview)
        return Created(
            target=target, files=files, added_dependencies=added, root_changes=tuple(root_changes)
        )

    root_pyproject = root / "pyproject.toml"
    original_pyproject = root_pyproject.read_text(encoding="utf-8")
    try:
        _render_unit(root / TEMPLATES_DIR / template, target, request, values)
        if request.kind == "app":
            _add_workspace_member(root_pyproject, rel_dir)
        else:
            _add_workspace_source(root_pyproject, values["dist"])
        write_generated(load_manifest(root))
    except (ValueError, ManifestError, SyntaxError):
        shutil.rmtree(target, ignore_errors=True)
        root_pyproject.write_text(original_pyproject, encoding="utf-8", newline="")
        raise
    return Created(
        target=target,
        files=_listing(target),
        added_dependencies=added,
        root_changes=tuple(root_changes),
    )


def _render_unit(
    template_dir: Path, target: Path, request: NewUnit, values: dict[str, str]
) -> None:
    """Gera a unidade em `target` e prova que o codigo Python gerado compila."""
    _render_tree(template_dir, target, values)
    for layer, doc in _LAYERS.get(request.kind, {}).items():
        init = target / "src" / values["import"] / layer / "__init__.py"
        init.parent.mkdir(parents=True, exist_ok=True)
        init.write_text(f'"""{doc}"""\n', encoding="utf-8", newline="")
    _compile_all(target)


def _listing(directory: Path) -> tuple[str, ...]:
    return tuple(
        sorted(p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file())
    )


def _template_values(
    request: NewUnit, by_id: dict, config: RepoConfig, rel_dir: str
) -> dict[str, str]:
    import_name = import_name_for(request.id, request.kind)
    dist = distribution_name_for(request.id, request.kind)
    owners = request.owners or config.default_owners
    required = [
        by_id[dep_id].distribution for dep_id in request.depends_on if by_id[dep_id].is_python
    ]
    description = (
        request.description or f"Unidade {request.id} ({request.kind}) do monorepo revold."
    )
    return {
        "id": request.id,
        "kind": request.kind,
        "product": f" {request.product}" if request.product else "",
        "lifecycle": request.lifecycle,
        "owners": _yaml_list(owners),
        "depends_on": _yaml_list(request.depends_on),
        "depends_on_text": ", ".join(f"`{d}`" for d in request.depends_on) or "nada",
        "import": import_name,
        "dist": dist,
        "description": description,
        "dependencies": ", ".join(_quote(d) for d in required),
        "rel_dir": rel_dir,
    }


def _quote(value: str) -> str:
    return f'"{value}"'


def _yaml_list(items: tuple[str, ...] | list[str]) -> str:
    return "[" + ", ".join(_quote(i) for i in items) + "]"


def _render_text(content: str, values: dict[str, str]) -> str:
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], content)


def _render_tree(source: Path, target: Path, values: dict[str, str]) -> None:
    """Copia o modelo trocando `{{chave}}` no conteudo e `__import__` nos caminhos."""
    for template_file in sorted(source.rglob("*.tmpl")):
        rel = template_file.relative_to(source).as_posix().removesuffix(".tmpl")
        rel = rel.replace("__import__", values["import"])
        out = target / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        rendered = _render_text(template_file.read_text(encoding="utf-8"), values)
        out.write_text(rendered, encoding="utf-8", newline="")


def _compile_all(target: Path) -> None:
    """Prova que o codigo gerado compila antes de dizer que deu certo."""
    for path in target.rglob("*.py"):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def _add_workspace_source(pyproject: Path, dist: str) -> None:
    """Acrescenta `<dist> = { workspace = true }` ao `[tool.uv.sources]` da raiz."""
    lines = pyproject.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("[tool.uv.sources]")
    except ValueError as exc:
        raise ValueError("o pyproject.toml da raiz nao tem [tool.uv.sources]") from exc
    end = start + 1
    while end < len(lines) and not lines[end].startswith("["):
        end += 1
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    if any(line.split("=")[0].strip() == dist for line in lines[start + 1 : end]):
        return
    lines.insert(end, f"{dist} = {{ workspace = true }}")
    pyproject.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")


def _add_workspace_member(pyproject: Path, rel_dir: str) -> None:
    """Acrescenta a pasta do app Python ao `members` do `[tool.uv.workspace]` da raiz.

    App mora em `apps/<produto>/<app>`, e o glob `apps/*` nao serve: o uv exige `pyproject.toml`
    em TODA pasta que o glob casa, e `apps/<produto>/` nao tem (nem os sites, que sao pnpm).
    Por isso cada app Python entra pelo caminho dele.
    """
    lines = pyproject.read_text(encoding="utf-8").splitlines()
    try:
        start = next(
            i for i, line in enumerate(lines) if line.replace(" ", "").startswith("members=[")
        )
        end = next(i for i in range(start, len(lines)) if lines[i].strip().startswith("]"))
    except StopIteration as exc:
        raise ValueError(
            "o pyproject.toml da raiz nao tem `members = [` em linhas separadas"
        ) from exc
    entry = f'"{rel_dir}"'
    if any(entry in line for line in lines[start:end]):
        return
    lines.insert(end, f"    {entry},")
    pyproject.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
