"""Seleciona a implementação de MediaStorage a partir de
MEDIA_STORAGE_PROVIDER.

Mesmo padrão de adapters_external.ai.factory / adapters_external.identity.factory
(ADR-0003/ADR-0011/ADR-0015).
"""
from __future__ import annotations

import os

from core_catalog.ports import MediaStorage

from adapters_external.media.local_filesystem_storage import LocalFilesystemStorage

_DEFAULT_LOCAL_DIR = "/app/media"


def get_media_storage() -> MediaStorage:
    provider = os.environ.get("MEDIA_STORAGE_PROVIDER", "local")
    if provider == "local":
        return LocalFilesystemStorage(
            base_dir=os.environ.get("MEDIA_STORAGE_LOCAL_DIR", _DEFAULT_LOCAL_DIR),
            base_url=os.environ.get("MEDIA_STORAGE_LOCAL_BASE_URL", "http://localhost:8000/media"),
        )
    if provider == "azure-blob":
        from adapters_external.media.azure_blob_storage import AzureBlobStorage

        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.environ.get("AZURE_STORAGE_CONTAINER", "product-images")
        if not connection_string:
            raise NotImplementedError(
                "MEDIA_STORAGE_PROVIDER=azure-blob requer AZURE_STORAGE_CONNECTION_STRING "
                "configurado (ver .env.example e ADR-0015)."
            )
        return AzureBlobStorage(
            connection_string=connection_string,
            container_name=container_name,
            public_base_url=os.environ.get("AZURE_STORAGE_PUBLIC_BASE_URL"),
        )
    raise ValueError(f"MEDIA_STORAGE_PROVIDER desconhecido: {provider!r}")
