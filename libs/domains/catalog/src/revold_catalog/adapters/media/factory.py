"""Seleciona a implementação de MediaStorage a partir de `MediaStorageSettings`.

Mesmo padrão das outras factories (ADR-0003/ADR-0011/ADR-0015).

Este módulo não lê o ambiente. O `settings.py` do app lê e entrega um `MediaStorageSettings`
pronto (em geral via `MediaStorageSettings.from_mapping(env_snapshot())`). Os nomes das chaves
são os do `.env.example`.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from revold_catalog.adapters.media.local_filesystem_storage import LocalFilesystemStorage
from revold_catalog.ports import MediaStorage

_DEFAULT_LOCAL_BASE_URL = "http://localhost:8000/media"
_DEFAULT_AZURE_CONTAINER = "product-images"


def default_local_dir() -> str:
    """Pasta local de mídia quando nenhuma é configurada.

    "/app" só existe dentro do container (WORKDIR do Dockerfile). Fora dele (CI do GitHub
    Actions, pytest direto na máquina de quem desenvolve) não há permissão para criar diretório
    na raiz do sistema de arquivos. Docker e produção continuam configurando
    `MEDIA_STORAGE_LOCAL_DIR=/app/media` explicitamente (docker-compose.yml); este é só o
    fallback para quando a variável não está configurada.
    """
    return str(Path(tempfile.gettempdir()) / "revold-media")


@dataclass(frozen=True)
class MediaStorageSettings:
    """Configuração do armazenamento de mídia. Segredo fica fora do `repr`."""

    provider: str = "local"
    local_dir: str = field(default_factory=default_local_dir)
    local_base_url: str = _DEFAULT_LOCAL_BASE_URL
    azure_connection_string: str | None = field(default=None, repr=False)
    azure_container: str = _DEFAULT_AZURE_CONTAINER
    azure_public_base_url: str | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> MediaStorageSettings:
        """Monta a configuração a partir de um mapeamento com as chaves do `.env.example`."""
        return cls(
            provider=values.get("MEDIA_STORAGE_PROVIDER", "local"),
            local_dir=values.get("MEDIA_STORAGE_LOCAL_DIR") or default_local_dir(),
            local_base_url=values.get("MEDIA_STORAGE_LOCAL_BASE_URL", _DEFAULT_LOCAL_BASE_URL),
            azure_connection_string=values.get("AZURE_STORAGE_CONNECTION_STRING"),
            azure_container=values.get("AZURE_STORAGE_CONTAINER", _DEFAULT_AZURE_CONTAINER),
            azure_public_base_url=values.get("AZURE_STORAGE_PUBLIC_BASE_URL"),
        )


def build_media_storage(settings: MediaStorageSettings | None = None) -> MediaStorage:
    settings = settings or MediaStorageSettings()
    provider = settings.provider
    if provider == "local":
        return LocalFilesystemStorage(base_dir=settings.local_dir, base_url=settings.local_base_url)
    if provider == "azure-blob":
        from revold_azure_blob.storage import AzureBlobStorage

        if not settings.azure_connection_string:
            raise NotImplementedError(
                "MEDIA_STORAGE_PROVIDER=azure-blob requer AZURE_STORAGE_CONNECTION_STRING "
                "configurado (ver .env.example e ADR-0015)."
            )
        return AzureBlobStorage(
            connection_string=settings.azure_connection_string,
            container_name=settings.azure_container,
            public_base_url=settings.azure_public_base_url,
        )
    raise ValueError(f"MEDIA_STORAGE_PROVIDER desconhecido: {provider!r}")
