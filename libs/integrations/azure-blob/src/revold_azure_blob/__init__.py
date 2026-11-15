"""Cliente do Azure Blob Storage: grava e apaga um blob e devolve a URL pública dele.

Não conhece catálogo nem produto. Quem o usa como armazenamento de imagem é a camada
`adapters/media/` do domínio `catalog` (ADR-0015).
"""

from revold_azure_blob.storage import AzureBlobStorage

__all__ = ["AzureBlobStorage"]
