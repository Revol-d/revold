"""Arquivos gerados a partir do manifesto: `.importlinter` e `.github/CODEOWNERS`.

Os dois sao saida, nunca entrada: `uv run dev gen` reescreve, e `uv run dev check` reprova
quando o commitado diverge do gerado.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from revold_tooling.manifest import Manifest, Unit

IMPORTLINTER_FILE = Path(".importlinter")
CODEOWNERS_FILE = Path(".github") / "CODEOWNERS"

_LAYERS = ("adapters", "application", "ports", "domain")


def generated_files(manifest: Manifest) -> dict[Path, str]:
    """Caminho relativo -> conteudo de cada arquivo gerado."""
    return {
        IMPORTLINTER_FILE: render_importlinter(manifest),
        CODEOWNERS_FILE: render_codeowners(manifest),
    }


def write_generated(manifest: Manifest) -> list[Path]:
    """Grava os arquivos gerados e devolve os que mudaram."""
    changed = []
    for rel, content in generated_files(manifest).items():
        path = manifest.root / rel
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            # `newline=""`: o repositorio e LF (.gitattributes); sem isto o Windows grava CRLF.
            path.write_text(content, encoding="utf-8", newline="")
            changed.append(rel)
    return changed


def stale_generated(manifest: Manifest) -> list[Path]:
    """Arquivos gerados cujo conteudo commitado diverge do que o manifesto produz."""
    stale = []
    for rel, content in generated_files(manifest).items():
        path = manifest.root / rel
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.is_file() else None
        if current != content:
            stale.append(rel)
    return stale


# --------------------------------------------------------------------- .importlinter
def _linted_units(manifest: Manifest) -> list[Unit]:
    """Unidades Python sob contrato. O app fica de fora: e o composition root e importa tudo."""
    return [u for u in manifest.python_units if u.kind != "app" and u.import_name]


def render_importlinter(manifest: Manifest) -> str:
    """O `.importlinter` inteiro, deterministico (mesma entrada, mesmo texto)."""
    units = _linted_units(manifest)
    by_id = manifest.by_id
    lines = [
        "# Gerado por `uv run dev gen` a partir dos unit.yaml. Nao edite a mao.",
        "#",
        "# Tres familias de contrato:",
        "#   1. cada unidade so importa o que declara em depends_on (regra D1, verificada tambem",
        "#      no manifesto);",
        "#   2. dominio e produto nao importam integracao fora de adapters/; application/ e ports/",
        "#      podem importar so os `pure_modules` que a integracao declara (modelos puros);",
        "#   3. camadas dentro de dominio e produto: adapters -> application -> ports -> domain; e, quando",
        "#      o unit.yaml declara `stages`, as etapas de application/.",
        "",
        "[importlinter]",
        "root_packages =",
        *(f"    {u.import_name}" for u in units),
        "",
    ]
    contracts: list[list[str]] = []

    for unit in units:
        allowed = {by_id[d].import_name for d in unit.depends_on if d in by_id}
        forbidden = sorted(
            u.import_name for u in units if u.import_name not in allowed and u.id != unit.id
        )
        if forbidden:
            contracts.append(
                _forbidden(
                    f"{unit.id} so importa o que declara em depends_on",
                    [unit.import_name],
                    forbidden,
                    allow_indirect=True,
                )
            )

    integration_units = sorted(
        (u for u in units if u.kind == "integration"), key=lambda u: u.import_name
    )
    integrations = [u.import_name for u in integration_units]
    # O que application/ e ports/ nao podem importar: a integracao inteira, ou, quando ela declara
    # `pure_modules`, so os submodulos que fazem I/O (clients, canais). "modelos puros".
    impure = sorted(
        f"{u.import_name}.{name}" if u.pure_modules else u.import_name
        for u in integration_units
        for name in (
            [m for m in u.top_level_modules() if m not in u.pure_modules]
            if u.pure_modules
            else [""]
        )
    )
    for unit in units:
        if not unit.is_layered or not integrations:
            continue
        contracts.append(
            _forbidden(
                f"{unit.id}: dominio nao importa integracao",
                [f"{unit.import_name}.domain"],
                integrations,
                allow_indirect=True,
            )
        )
        sources = [f"{unit.import_name}.{layer}" for layer in ("application", "ports")]
        contracts.append(
            _forbidden(
                f"{unit.id}: integracao com I/O so entra pela camada adapters",
                sources,
                impure,
                allow_indirect=True,
            )
        )
        contracts.append(_layers(f"{unit.id}: camadas", unit.import_name))
        if unit.stages:
            # As etapas de application/ em camadas, para o produto poder ser dividido sem refatorar.
            contracts.append(
                _layers(f"{unit.id}: etapas", f"{unit.import_name}.application", unit.stages)
            )

    for number, body in enumerate(contracts, start=1):
        lines.append(f"[importlinter:contract:{number}]")
        lines.extend(body)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def _forbidden(
    name: str, sources: Iterable[str], forbidden: Iterable[str], *, allow_indirect: bool
) -> list[str]:
    body = [f"name = {name}", "type = forbidden", "source_modules ="]
    body += [f"    {s}" for s in sources]
    body += ["forbidden_modules ="]
    body += [f"    {f}" for f in forbidden]
    if allow_indirect:
        # Import indireto (A importa B, que importa C) nao conta: a regra e sobre o que a
        # unidade importa DIRETAMENTE. Sem isto, o app ou o produto reprovariam por causa
        # das dependencias das suas dependencias.
        body.append("allow_indirect_imports = True")
    return body


def _layers(name: str, container: str, layers: Iterable[str] = _LAYERS) -> list[str]:
    return [
        f"name = {name}",
        "type = layers",
        "containers =",
        f"    {container}",
        "layers =",
        *(f"    {layer}" for layer in layers),
    ]


# --------------------------------------------------------------------- CODEOWNERS
def render_codeowners(manifest: Manifest) -> str:
    """O `.github/CODEOWNERS` inteiro: padrao, unidades, plataforma e os proprios manifestos."""
    config = manifest.config
    rules: list[tuple[str, tuple[str, ...]]] = []
    unit_rules = [
        (f"/{u.rel_dir}/", u.owners) for u in sorted(manifest.units, key=lambda u: u.rel_dir)
    ]
    platform_rules = [(path, config.platform_owners) for path in config.platform_paths]
    manifest_rules = [
        (f"/{u.rel_dir}/unit.yaml", config.platform_owners)
        for u in sorted(manifest.units, key=lambda u: u.rel_dir)
    ]
    rules = [("*", config.default_owners), *unit_rules, *platform_rules, *manifest_rules]
    width = max(len(path) for path, _ in rules) + 2

    def block(title: list[str], items: list[tuple[str, tuple[str, ...]]]) -> list[str]:
        return [*title, *(f"{path:<{width}}{' '.join(owners)}" for path, owners in items), ""]

    lines = [
        "# Gerado por `uv run dev gen` a partir dos unit.yaml e de tooling/repo.yaml. Nao edite a mao.",
        "#",
        "# Para trocar o dono de uma unidade, edite o `owners` do unit.yaml dela e rode `uv run dev gen`.",
        "# Por que cada regra existe e o que falha em silencio: docs/branch-strategy.md, secao",
        '# "Revisao de PR — CODEOWNERS". A ULTIMA regra que casar e a que vale.',
        "",
        *block(["# Tudo, por padrao."], [rules[0]]),
        *block(["# Unidades (owners do unit.yaml)."], unit_rules),
        *block(["# Plataforma: gates, tooling e deploy."], platform_rules),
        *block(
            [
                "# Os proprios manifestos sao da plataforma (ADR-0030): ninguem se poe como dono de",
                "# uma unidade e aprova o proprio PR.",
            ],
            manifest_rules,
        ),
    ]
    return "\n".join(lines).rstrip("\n") + "\n"
