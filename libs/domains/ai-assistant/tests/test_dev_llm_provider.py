from __future__ import annotations

from revold_ai_assistant.adapters.llm.dev_llm_provider import EMBEDDING_DIMENSIONS, DevLLMProvider
from revold_ai_assistant.domain import ChatMessage, Role


async def test_embed_e_deterministico() -> None:
    provider = DevLLMProvider()
    first = await provider.embed("vestido floral")
    second = await provider.embed("vestido floral")
    assert first == second
    assert len(first) == EMBEDDING_DIMENSIONS


async def test_embed_textos_diferentes_geram_vetores_diferentes() -> None:
    provider = DevLLMProvider()
    a = await provider.embed("vestido floral")
    b = await provider.embed("bolsa de couro")
    assert a != b


async def test_complete_sem_produtos_no_prompt_sugere_whatsapp() -> None:
    provider = DevLLMProvider()
    reply = await provider.complete(
        system_prompt="Você é a assistente virtual da loja da Nick.",
        messages=[ChatMessage(role=Role.USER, content="Vocês têm bolsas?")],
    )
    assert "WhatsApp" in reply
    assert "Vocês têm bolsas?" in reply


async def test_complete_com_produtos_no_prompt_menciona_que_encontrou() -> None:
    provider = DevLLMProvider()
    reply = await provider.complete(
        system_prompt=(
            "Você é a assistente virtual da loja da Nick.\n\n"
            "Produtos do catálogo relevantes para a pergunta:\n- Vestido Floral (SKU A)"
        ),
        messages=[ChatMessage(role=Role.USER, content="Tem vestido floral?")],
    )
    assert "Encontrei algumas opções" in reply
