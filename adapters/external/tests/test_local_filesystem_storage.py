"""Testa LocalFilesystemStorage — sem nenhuma infraestrutura, só o
filesystem do teste (tmp_path)."""
from __future__ import annotations

from pathlib import Path

from adapters_external.media.local_filesystem_storage import LocalFilesystemStorage


async def test_upload_grava_arquivo_e_retorna_url(tmp_path: Path) -> None:
    storage = LocalFilesystemStorage(base_dir=tmp_path, base_url="http://localhost:8000/media")

    url = await storage.upload(key="products/A/foto.jpg", content=b"conteudo", content_type="image/jpeg")

    assert url == "http://localhost:8000/media/products/A/foto.jpg"
    assert (tmp_path / "products" / "A" / "foto.jpg").read_bytes() == b"conteudo"


async def test_upload_cria_subdiretorios_que_nao_existem(tmp_path: Path) -> None:
    storage = LocalFilesystemStorage(base_dir=tmp_path, base_url="http://x")

    await storage.upload(key="a/b/c/imagem.png", content=b"x", content_type="image/png")

    assert (tmp_path / "a" / "b" / "c" / "imagem.png").exists()


async def test_delete_remove_arquivo_existente(tmp_path: Path) -> None:
    storage = LocalFilesystemStorage(base_dir=tmp_path, base_url="http://x")
    await storage.upload(key="foto.jpg", content=b"x", content_type="image/jpeg")

    await storage.delete("foto.jpg")

    assert not (tmp_path / "foto.jpg").exists()


async def test_delete_de_arquivo_inexistente_nao_levanta_erro(tmp_path: Path) -> None:
    storage = LocalFilesystemStorage(base_dir=tmp_path, base_url="http://x")

    await storage.delete("nunca-existiu.jpg")  # não deve levantar
