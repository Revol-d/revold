"""Adapter de desenvolvimento de revold_catalog.ports.MediaStorage (ADR-0015).

Grava em disco local, dentro do container do api-gateway — serve para
desenvolver e testar sem nenhuma credencial de nuvem. `api_gateway.main`
monta este diretório como arquivos estáticos em /media (ver lá) para as
URLs devolvidas por `upload` funcionarem de verdade em dev.
"""
from __future__ import annotations

from pathlib import Path


class LocalFilesystemStorage:
    provider_name = "local"

    def __init__(self, base_dir: Path | str, base_url: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._base_url = base_url.rstrip("/")

    async def upload(self, *, key: str, content: bytes, content_type: str) -> str:
        path = self._base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return f"{self._base_url}/{key}"

    async def delete(self, key: str) -> None:
        path = self._base_dir / key
        path.unlink(missing_ok=True)
