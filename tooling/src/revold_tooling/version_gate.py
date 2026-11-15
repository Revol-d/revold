"""Gate do `dev check`: codigo mudou desde o ultimo release e a versao nao subiu? Falha.

E a regra que impede o mesmo numero de versao de ter dois conteudos. O ponto de comparacao e o
BOM do ultimo release de cada app (`.releases/<app>.json`), que guarda o sha256 do `src/` de
cada unidade do fecho. Nao depende do historico do git: funciona em clone raso e antes do
commit, que e quando o aviso sai barato.

Conta como "codigo" o que vai para dentro da imagem: o `src/` da unidade. Teste, README e
`unit.yaml` nao mudam o que o app instala. O proprio app fica de fora: a versao dele so sobe no
`dev release`, que e justamente o que publica a mudanca.
"""

from __future__ import annotations

from dataclasses import dataclass

from revold_tooling.manifest import Manifest, normalize_distribution
from revold_tooling.release import released_bom, sha256_of_source


@dataclass(frozen=True)
class StaleVersion:
    """Uma unidade cujo codigo mudou sem a versao subir."""

    app: str
    unit: str
    version: str

    def __str__(self) -> str:
        return (
            f"{self.unit}: o src/ mudou desde o release de {self.app} e a versao continua "
            f"{self.version}. Rode `uv run dev bump {self.unit} patch`."
        )


def stale_versions(manifest: Manifest) -> tuple[list[StaleVersion], list[str]]:
    """As unidades com versao velha, e os avisos de por que o gate nao pode olhar algo.

    App sem release gravado nao tem ponto de comparacao: o gate o pula e DIZ que pulou. Gate
    que pula calado parece protecao e nao e.
    """
    stale: list[StaleVersion] = []
    notes: list[str] = []
    seen: set[str] = set()
    for app in (u for u in manifest.units if u.kind == "app" and u.is_python):
        path, bom = released_bom(manifest, app)
        if bom is None or path is None:
            notes.append(
                f"{app.id} ainda nao tem release (.releases/{app.id}.json): nada a comparar"
            )
            continue
        released = {normalize_distribution(e.unidade): e for e in bom.unidades}
        for unit in manifest.closure(app.id):
            if unit.id == app.id or not unit.is_python or unit.id in seen:
                continue
            entry = released.get(unit.distribution)
            if entry is None or entry.versao != unit.version:
                continue
            if sha256_of_source(unit.src_dir) != entry.sha256:
                seen.add(unit.id)
                stale.append(StaleVersion(app=app.id, unit=unit.id, version=unit.version))
    return stale, notes
