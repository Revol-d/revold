# ADR-0015: MediaStorage — upload de imagem de produto (blob storage)

**Status:** Aceito

## Contexto

O catálogo (`core_catalog.domain.Product.images`) sempre aceitou uma lista de URLs de imagem, mas só de um jeito: colar a URL à mão em `POST/PATCH /api/catalog/products` (`images: ["https://..."]`). Não existia nenhum caminho para efetivamente enviar um arquivo de imagem — quem cadastra um produto precisaria hospedar a foto em algum outro lugar antes, fora do sistema.

Isso é uma lacuna real para o piloto da Nick (cadastro de produto pelo admin precisa aceitar upload de arquivo, não só URL) e também um leaf genérico e reutilizável: qualquer projeto futuro do framework vai precisar guardar arquivo binário (imagem, mas também poderia ser PDF, planilha etc.) em algum blob storage.

Enquanto a credencial real de nuvem (Azure Storage de produção) segue indisponível, o objetivo é ter o port + os dois adapters de sempre (dev barato, e um adapter real validado contra um backend real, mesmo que emulado) prontos e testados, faltando só trocar a credencial quando ela existir — mesmo padrão já usado em ADR-0003 (auth), ADR-0006/0011 (LLM), ADR-0012 (Postgres real no CI).

## Decisão

**Porta nova em core-catalog** (não um core novo — upload de imagem é uma operação do catálogo, não um bounded context à parte): `core_catalog.ports.MediaStorage`:

```python
class MediaStorage(Protocol):
    async def upload(self, *, key: str, content: bytes, content_type: str) -> str: ...
    async def delete(self, key: str) -> None: ...
```

Genérica de propósito (`key`/`content`/`content_type`, sem nada específico de "imagem de produto") para servir qualquer necessidade futura de blob storage do framework, não só fotos de produto.

**Caso de uso novo**: `core_catalog.use_cases.AddProductImage` — busca o produto, sanitiza o nome do arquivo (`_UNSAFE_FILENAME_CHARS`, troca qualquer caractere fora de `[A-Za-z0-9_.-]` por `_`; isso principalmente elimina barras, o que impede o nome do arquivo de criar um novo segmento de caminho fora do prefixo fixo `products/{sku}/{uuid}-`), monta uma chave única (`products/{sku}/{uuid4().hex}-{nome_sanitizado}`), envia via `MediaStorage.upload`, e acrescenta a URL resultante a `product.images`.

**Adapters** (`adapters/external/src/adapters_external/media/`):
- `LocalFilesystemStorage` (dev/default): grava em disco dentro do próprio container do api-gateway; `api_gateway.main` monta esse diretório como estáticos em `/media` para as URLs devolvidas funcionarem de verdade em dev, sem depender de nenhum serviço externo.
- `AzureBlobStorage` (real): usa `azure-storage-blob` (cliente assíncrono, `azure.storage.blob.aio.BlobServiceClient`). Validado de ponta a ponta contra o **Azurite** — emulador oficial da Microsoft para Azure Storage, que fala o protocolo Blob de verdade — usando a connection string "well-known" pública e documentada do próprio Azurite (não é segredo). Zero credencial Azure real precisou existir para provar que o adapter funciona.

Seleção via `MEDIA_STORAGE_PROVIDER` (`local` por padrão, `azure-blob` quando configurado — ver `adapters_external.media.factory.get_media_storage`), mesmo padrão de `LLM_PROVIDER`/`AUTH_PROVIDER`/`EVENT_PUBLISHER`.

**Endpoint HTTP novo**: `POST /api/catalog/products/{sku}/images`, multipart (`UploadFile`), RBAC STAFF/ADMIN — diferente de `PATCH /api/catalog/products/{sku}` (que só substitui a lista inteira de imagens por URLs já conhecidas). Guardas aplicadas no router, antes de chegar no caso de uso: tipo de conteúdo (`image/jpeg`, `image/png`, `image/webp`) e tamanho máximo (10MB).

## Testes

- `cores/core-catalog/tests/test_use_cases.py::TestAddProductImage`: upload com sucesso, sanitização de nome de arquivo perigoso, produto inexistente levanta `ProductNotFound` — tudo com `FakeMediaStorage` em memória.
- `adapters/external/tests/test_local_filesystem_storage.py`: grava/lê/apaga de verdade em `tmp_path`.
- `adapters/external/tests/test_azure_blob_storage.py` (`@pytest.mark.integration`): sobe um processo real do Azurite, confirma upload/content-type/delete lendo de volta via um cliente Azure independente do adapter. Pula sozinho se o binário `azurite` não estiver instalado.
- `apps/api-gateway/tests/test_catalog_routes.py`: contrato HTTP do endpoint — upload com sucesso (STAFF/ADMIN), sanitização de nome perigoso não vaza fora do prefixo esperado, tipo não suportado → 422, arquivo grande demais → 422, SKU inexistente → 404, sem autenticação → 401, papel CUSTOMER → 403.

## Consequências

- `core_catalog.domain.Product.images` continua sendo só `list[str]` — nenhuma mudança de schema/contrato downstream (storefront/admin continuam recebendo URLs simples).
- `apps/api-gateway/src/api_gateway/main.py` monta `/media` como estáticos — sem efeito quando `MEDIA_STORAGE_PROVIDER=azure-blob` (diretório local fica vazio, mas não quebra nada).
- Trocar para Azure real de produção é só configurar `AZURE_STORAGE_CONNECTION_STRING`/`AZURE_STORAGE_CONTAINER`/`MEDIA_STORAGE_PROVIDER=azure-blob` — nenhum código muda.
- Base pronta para qualquer outro tipo de arquivo binário que um projeto futuro do framework precise guardar (PDF, planilha, anexo) reaproveitando a mesma porta.
