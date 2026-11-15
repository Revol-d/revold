"""Unidades afetadas por uma mudanca: arquivos -> unidades -> consumidores (fecho reverso)."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass

from revold_tooling.manifest import Manifest


@dataclass(frozen=True)
class Affected:
    """Resultado do calculo, com o motivo de cada unidade entrar."""

    units: tuple[str, ...]
    changed: tuple[str, ...]
    global_change: bool

    @property
    def any(self) -> bool:
        """Ha alguma unidade a testar."""
        return bool(self.units)


def changed_files(manifest: Manifest, base: str) -> list[str]:
    """Arquivos alterados desde o ponto em que a branch saiu de `base`, mais os nao commitados.

    `base...HEAD` (tres pontos) compara com o ancestral comum: o que a `main` andou depois
    que a branch saiu nao entra na conta.
    """

    def git(*args: str) -> list[str]:
        result = subprocess.run(
            ["git", *args], cwd=manifest.root, capture_output=True, text=True, check=True
        )
        return [line for line in result.stdout.splitlines() if line]

    files = set(git("diff", "--name-only", f"{base}...HEAD"))
    files.update(git("diff", "--name-only", "HEAD"))
    files.update(git("ls-files", "--others", "--exclude-standard"))
    return sorted(files)


def compute_affected(manifest: Manifest, files: Iterable[str]) -> Affected:
    """Unidades tocadas pelos arquivos e todas as que dependem delas, direta ou indiretamente."""
    files = sorted({f.replace("\\", "/") for f in files})
    config = manifest.config
    units_by_dir = sorted(
        ((u.rel_dir + "/", u.id) for u in manifest.units), key=lambda item: -len(item[0])
    )
    all_ids = {u.id for u in manifest.units}

    touched: set[str] = set()
    global_change = False
    for path in files:
        owner = next((unit_id for prefix, unit_id in units_by_dir if path.startswith(prefix)), None)
        if owner:
            touched.add(owner)
        elif any(
            path == g or (g.endswith("/") and path.startswith(g)) for g in config.affected_global
        ):
            global_change = True
        else:
            for prefix, unit_ids in config.affected_paths.items():
                if path.startswith(prefix):
                    touched.update(u for u in unit_ids if u in all_ids)

    if global_change:
        return Affected(units=tuple(sorted(all_ids)), changed=tuple(files), global_change=True)

    consumers = manifest.consumers()
    result = set(touched)
    pending = list(touched)
    while pending:
        for consumer in consumers.get(pending.pop(), ()):
            if consumer not in result:
                result.add(consumer)
                pending.append(consumer)
    return Affected(units=tuple(sorted(result)), changed=tuple(files), global_change=False)
