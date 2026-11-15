# `revold_azure_blob`

Cliente do Azure Blob Storage: grava e apaga um blob e devolve a URL pública dele.

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

`AzureBlobStorage(connection_string, container_name, public_base_url)`: `upload` e `delete`. Exercitado de ponta a ponta contra o Azurite, o emulador oficial (ADR-0015).

## O que NÃO faz

- **Não conhece catálogo nem produto.** Quem o usa como armazenamento de imagem é `adapters/media/` do domínio `catalog`.
- **Não lê `AZURE_STORAGE_*`.** A configuração chega por parâmetro.

## Testes

```powershell
uv run pytest libs/integrations/azure-blob/tests -q
```
