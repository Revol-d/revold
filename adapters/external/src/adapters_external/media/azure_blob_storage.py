"""Adapter real de core_catalog.ports.MediaStorage — Azure Blob Storage
(ADR-0015).

Testado de ponta a ponta contra o Azurite (emulador oficial da Microsoft
para Azure Storage, `mcr.microsoft.com/azure-storage/azurite` / pacote npm
`azurite`) — fala o protocolo Blob real, então este adapter é exercitado
de verdade sem precisar de uma conta Azure real (ver
adapters/external/tests/test_azure_blob_storage.py). Só falta a connection
string de uma conta real pra usar em produção; o código não muda.
"""
from __future__ import annotations

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient


class AzureBlobStorage:
    provider_name = "azure-blob"

    def __init__(
        self, *, connection_string: str, container_name: str, public_base_url: str | None = None
    ) -> None:
        self._connection_string = connection_string
        self._container_name = container_name
        self._public_base_url = public_base_url

    async def upload(self, *, key: str, content: bytes, content_type: str) -> str:
        async with BlobServiceClient.from_connection_string(self._connection_string) as service:
            container = service.get_container_client(self._container_name)
            try:
                await container.create_container()
            except ResourceExistsError:
                pass
            blob = container.get_blob_client(key)
            await blob.upload_blob(
                content,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
            return self._public_url(key)

    async def delete(self, key: str) -> None:
        async with BlobServiceClient.from_connection_string(self._connection_string) as service:
            container = service.get_container_client(self._container_name)
            blob = container.get_blob_client(key)
            try:
                await blob.delete_blob()
            except ResourceNotFoundError:
                # Idempotente — mesma convenção de delete_product/delete_category
                # (core_catalog): não é erro apagar algo que já não existe.
                pass

    def _public_url(self, key: str) -> str:
        if self._public_base_url:
            return f"{self._public_base_url.rstrip('/')}/{key}"
        # Sem CDN/domínio próprio configurado: usa a URL pública padrão do
        # próprio Storage Account (container precisa ter acesso público de
        # leitura configurado do lado do Azure para isso funcionar de fato).
        account_url = self._connection_string_account_url()
        return f"{account_url}/{self._container_name}/{key}"

    def _connection_string_account_url(self) -> str:
        parts = dict(
            item.split("=", 1) for item in self._connection_string.split(";") if "=" in item
        )
        protocol = parts.get("DefaultEndpointsProtocol", "https")
        account = parts.get("AccountName", "")
        suffix = parts.get("EndpointSuffix", "core.windows.net")
        blob_endpoint = parts.get("BlobEndpoint")
        if blob_endpoint:
            return blob_endpoint.rstrip("/")
        return f"{protocol}://{account}.blob.{suffix}"
