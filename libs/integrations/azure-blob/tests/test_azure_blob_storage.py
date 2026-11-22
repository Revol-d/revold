"""Teste de integração real do AzureBlobStorage contra o Azurite (emulador
oficial da Microsoft para Azure Storage — fala o protocolo Blob real, sem
nenhuma credencial Azure de verdade). Mesma convenção dos outros testes de
integração deste monorepo: pula sozinho se o binário `azurite` não estiver
disponível (ver libs/domains/<dominio>/tests/test_catalog_repository_integration_azure_sql.py
para o equivalente com Azure SQL real).

A connection string usada é a "well-known" do próprio Azurite — pública,
documentada pela Microsoft, não é um segredo (https://learn.microsoft.com/
azure/storage/common/storage-use-azurite#well-known-storage-account-and-key).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time

import pytest

pytestmark = pytest.mark.integration

_AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)


@pytest.fixture(scope="module")
def azurite_process():
    azurite_bin = shutil.which("azurite-blob") or shutil.which("azurite")
    if azurite_bin is None:
        pytest.skip("binário azurite não encontrado — pulando teste de integração.")

    data_dir = tempfile.mkdtemp(prefix="azurite-test-")
    args = [azurite_bin, "--location", data_dir, "--silent"]
    if azurite_bin.endswith("azurite"):
        args = [azurite_bin, "--blobHost", "127.0.0.1", "--blobPort", "10000", "--location", data_dir, "--silent"]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    _wait_for_port(("127.0.0.1", 10000), timeout=20, proc=proc)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _wait_for_port(address: tuple[str, int], *, timeout: float, proc: subprocess.Popen) -> None:
    import socket

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"azurite encerrou antes de ficar pronto:\n{output}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect(address)
                return
            except OSError:
                time.sleep(0.3)
    raise TimeoutError(f"azurite não abriu a porta {address} a tempo")


@pytest.fixture
def storage(azurite_process):
    from revold_azure_blob.storage import AzureBlobStorage

    return AzureBlobStorage(
        connection_string=_AZURITE_CONNECTION_STRING,
        container_name=f"test-container-{int(time.time() * 1000)}",
    )


async def test_upload_grava_de_verdade_e_retorna_url(storage) -> None:
    url = await storage.upload(
        key="products/CAM-001/foto.jpg", content=b"conteudo-de-verdade", content_type="image/jpeg"
    )

    assert "products/CAM-001/foto.jpg" in url

    # confirma que o blob existe de verdade lendo de volta via um cliente
    # independente do adapter (não confia só no retorno do upload)
    from azure.storage.blob.aio import BlobServiceClient

    async with BlobServiceClient.from_connection_string(_AZURITE_CONNECTION_STRING) as service:
        container = service.get_container_client(storage._container_name)
        blob = container.get_blob_client("products/CAM-001/foto.jpg")
        downloaded = await (await blob.download_blob()).readall()
        assert downloaded == b"conteudo-de-verdade"


async def test_upload_preserva_content_type(storage) -> None:
    await storage.upload(key="a.png", content=b"x", content_type="image/png")

    from azure.storage.blob.aio import BlobServiceClient

    async with BlobServiceClient.from_connection_string(_AZURITE_CONNECTION_STRING) as service:
        container = service.get_container_client(storage._container_name)
        blob = container.get_blob_client("a.png")
        properties = await blob.get_blob_properties()
        assert properties.content_settings.content_type == "image/png"


async def test_delete_remove_blob_de_verdade(storage) -> None:
    await storage.upload(key="apagar.jpg", content=b"x", content_type="image/jpeg")

    await storage.delete("apagar.jpg")

    from azure.core.exceptions import ResourceNotFoundError
    from azure.storage.blob.aio import BlobServiceClient

    async with BlobServiceClient.from_connection_string(_AZURITE_CONNECTION_STRING) as service:
        container = service.get_container_client(storage._container_name)
        blob = container.get_blob_client("apagar.jpg")
        with pytest.raises(ResourceNotFoundError):
            await blob.get_blob_properties()


async def test_delete_de_blob_inexistente_nao_levanta_erro(storage) -> None:
    await storage.delete("nunca-existiu.jpg")  # não deve levantar
