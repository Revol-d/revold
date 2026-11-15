"""Vetor de um texto por um deployment de embeddings da Azure OpenAI (via langchain-openai)."""

from __future__ import annotations

from revold_openai.chat import DEFAULT_AZURE_API_VERSION


class AzureOpenAIEmbeddings:
    """Embeddings de um deployment da Azure OpenAI."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = DEFAULT_AZURE_API_VERSION,
    ) -> None:
        from langchain_openai import AzureOpenAIEmbeddings as _LangchainAzureOpenAIEmbeddings
        from pydantic import SecretStr

        self._embeddings = _LangchainAzureOpenAIEmbeddings(
            azure_endpoint=endpoint,
            api_key=SecretStr(api_key),
            azure_deployment=deployment,
            api_version=api_version,
            # Sem isto, langchain-openai baixa o arquivo de encoding do
            # tiktoken de um blob storage público da Microsoft na primeira
            # chamada (rede real, fora do controle do cliente) só pra
            # contar/cortar tokens localmente antes de mandar pra API. Numa
            # rede com egress restrito (como o Terraform deste projeto se
            # propõe a controlar) isso pode falhar silenciosamente na
            # primeira chamada em produção. Descrição de produto é curta o
            # bastante pra não precisar de corte local — deixa a Azure
            # rejeitar com 400 no caso raro de passar do limite, em vez de
            # depender dessa chamada de rede escondida.
            check_embedding_ctx_length=False,
        )

    async def embed(self, text: str) -> list[float]:
        return await self._embeddings.aembed_query(text)
