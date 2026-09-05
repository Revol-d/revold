from __future__ import annotations

from core_ai_assistant.domain import ChatMessage, Role
from core_ai_assistant.use_cases import AskAssistant, IndexProduct


async def test_index_product_embeda_e_faz_upsert(fake_llm, fake_index) -> None:
    await IndexProduct(fake_llm, fake_index).execute(
        sku="A", name="Vestido Floral", description="Vestido leve de verão"
    )
    assert fake_llm.embed_calls == ["Vestido Floral\nVestido leve de verão"]

    results = await fake_index.search(embedding=await fake_llm.embed("qualquer coisa"), limit=1)
    assert results[0].sku == "A"


async def test_ask_assistant_sem_produtos_indexados_nao_encontra_nada(fake_llm, fake_index) -> None:
    reply = await AskAssistant(fake_llm, fake_index).execute(history=[], question="Vocês têm bolsas?")
    assert reply.retrieved_products == ()
    assert "sem produtos" in reply.message
    assert reply.escalate_to_whatsapp is False


async def test_ask_assistant_com_produto_indexado_retorna_produto_relevante(fake_llm, fake_index) -> None:
    await IndexProduct(fake_llm, fake_index).execute(
        sku="A", name="Vestido Floral", description="Vestido leve de verão"
    )

    reply = await AskAssistant(fake_llm, fake_index).execute(
        history=[], question="Tem vestido floral?"
    )

    assert len(reply.retrieved_products) == 1
    assert reply.retrieved_products[0].sku == "A"
    assert "encontrei produtos" in reply.message


async def test_ask_assistant_com_intencao_de_compra_escala_para_whatsapp(fake_llm, fake_index) -> None:
    reply = await AskAssistant(fake_llm, fake_index).execute(
        history=[], question="Quero comprar o vestido floral, como faço?"
    )
    assert reply.escalate_to_whatsapp is True


async def test_ask_assistant_sem_intencao_de_compra_nao_escala(fake_llm, fake_index) -> None:
    reply = await AskAssistant(fake_llm, fake_index).execute(
        history=[], question="Vocês têm entrega para o Rio de Janeiro?"
    )
    assert reply.escalate_to_whatsapp is False


async def test_ask_assistant_usa_historico_no_prompt(fake_llm, fake_index) -> None:
    history = [
        ChatMessage(role=Role.USER, content="Oi"),
        ChatMessage(role=Role.ASSISTANT, content="Olá! Como posso ajudar?"),
    ]
    await AskAssistant(fake_llm, fake_index).execute(history=history, question="Tem vestido azul?")

    _system_prompt, messages = fake_llm.complete_calls[-1]
    assert messages[0] == history[0]
    assert messages[1] == history[1]
    assert messages[-1].content == "Tem vestido azul?"
