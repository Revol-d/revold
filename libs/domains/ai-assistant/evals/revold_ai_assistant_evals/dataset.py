"""Dataset comportamental do assistente de IA (`AskAssistant`) — a peça que
faltava: `libs/domains/ai-assistant/tests/test_use_cases.py` cobre a lógica
com só 6 casos escolhidos a dedo. Aqui são 14 perguntas plausíveis de
cliente da loja da Nick (linguagem informal, emoji, pergunta vazia, texto
longo, e as variações de várias frases-gatilho de intenção de compra),
cada uma com o comportamento esperado — pensado pra rodar de dois jeitos
diferentes (ver `test_behavior.py` e `test_llm_judge.py`):

1. **Comportamental** (`expect_escalation`/`expect_retrieval`): determinístico,
   independente de provedor de LLM — roda sempre, com qualquer
   `LLMProvider`/`ProductIndex` (fake ou real). Testa a lógica de
   orquestração (heurística de escalar pro WhatsApp, se a busca aconteceu),
   não a qualidade da resposta.
2. **Qualidade** (`criterio_qualidade`): só faz sentido com um LLM de
   verdade avaliando a resposta de outro LLM de verdade (LLM-as-judge) —
   com o provider `dev` a resposta é sempre o mesmo texto de regra fixa,
   então pontuar "qualidade" dela não mediria nada real.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from revold_ai_assistant.domain import ChatMessage, Role


@dataclass(frozen=True, slots=True)
class IndexedProduct:
    """Um produto "no catálogo" só para o propósito deste caso de teste —
    não é o Product de revold_catalog (os dois cores nunca se importam)."""

    sku: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class EvalCase:
    id: str
    question: str
    catalog: tuple[IndexedProduct, ...]
    expect_escalation: bool
    expect_retrieval: bool
    criterio_qualidade: str
    history: tuple[ChatMessage, ...] = field(default_factory=tuple)


_VESTIDO = IndexedProduct(
    sku="VES-001", name="Vestido Midi Floral", description="Vestido midi estampa floral, tecido leve"
)
_CALCA = IndexedProduct(
    sku="CAL-001", name="Calça Jeans Reta", description="Calça jeans reta cintura alta"
)
_BLUSA = IndexedProduct(
    sku="BLU-001", name="Blusa de Tricô Gola Alta", description="Blusa de tricô gola alta, inverno"
)

_CATALOGO_PADRAO = (_VESTIDO, _CALCA, _BLUSA)

DATASET: tuple[EvalCase, ...] = (
    EvalCase(
        id="produto_existe_no_catalogo",
        question="Vocês têm vestido floral?",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=False,
        expect_retrieval=True,
        criterio_qualidade=(
            "Deve confirmar que há vestido floral disponível, sem inventar cor/tamanho "
            "que não foi perguntado."
        ),
    ),
    EvalCase(
        id="produto_nao_existe_no_catalogo",
        question="Vocês têm bolsa de couro?",
        catalog=(),
        expect_escalation=False,
        expect_retrieval=False,
        criterio_qualidade=(
            "Não deve inventar que tem bolsa — deve dizer que não encontrou e sugerir "
            "falar com a Nick, sem fechar a porta pro cliente."
        ),
    ),
    EvalCase(
        id="intencao_de_compra_explicita",
        question="Quero comprar o vestido floral, como faço?",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=True,
        expect_retrieval=True,
        criterio_qualidade="Deve direcionar para o WhatsApp da Nick, não tentar fechar a venda sozinha.",
    ),
    EvalCase(
        # expect_retrieval=True aqui documenta uma característica REAL (não
        # necessariamente desejável) do fluxo atual: `retrieve` em
        # use_cases.py não tem corte de relevância — se o índice tem
        # qualquer produto, ele sempre entra no prompt como "relevante",
        # mesmo numa pergunta de frete que não tem nada a ver com produto
        # nenhum. O critério de qualidade abaixo é o que cobre isso: o LLM
        # (não a recuperação) é quem precisa ignorar contexto irrelevante.
        id="pergunta_sobre_frete_sem_intencao_de_compra",
        question="Vocês entregam para o Rio de Janeiro?",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=False,
        expect_retrieval=True,
        criterio_qualidade=(
            "Não deve inventar prazo/valor de frete que não foi decidido pelo negócio, e não "
            "deve responder com uma lista de produtos como se isso respondesse a pergunta de frete."
        ),
    ),
    EvalCase(
        id="pergunta_informal_com_emoji_e_girias",
        question="Oi né, cê tem uma calça daora aí? 😍✨",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=False,
        expect_retrieval=True,
        criterio_qualidade="Deve entender a pergunta apesar da informalidade, sem tom de deboche.",
    ),
    EvalCase(
        id="pergunta_vazia",
        question="",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=False,
        expect_retrieval=True,
        criterio_qualidade=(
            "Pergunta vazia não deve quebrar o assistente — resposta deve pedir para o "
            "cliente reformular, não travar nem devolver algo sem sentido."
        ),
    ),
    EvalCase(
        id="pergunta_muito_longa",
        question=(
            "Oi, então eu vi um post no Instagram de vocês outro dia e fiquei super "
            "interessada, só que aí eu tava olhando o site e não sei se aquele vestido que "
            "apareceu lá ainda tem no tamanho que eu uso, que geralmente é M mas às vezes "
            "veste como G dependendo do tecido, será que dá pra me ajudar a entender melhor "
            "as opções que vocês têm de vestido, tipo estampa floral ou lisa, e também se "
            "tem alguma promoção rolando essa semana?"
        ),
        catalog=_CATALOGO_PADRAO,
        expect_escalation=False,
        expect_retrieval=True,
        criterio_qualidade="Deve responder à pergunta central (vestidos disponíveis) sem se perder no texto longo.",
    ),
    EvalCase(
        id="historico_influencia_resposta",
        question="E tem em azul?",
        catalog=_CATALOGO_PADRAO,
        history=(
            ChatMessage(role=Role.USER, content="Tem vestido floral?"),
            ChatMessage(role=Role.ASSISTANT, content="Temos sim! O Vestido Midi Floral está disponível."),
        ),
        expect_escalation=False,
        expect_retrieval=True,
        criterio_qualidade="Deve interpretar 'tem em azul' como continuação da pergunta sobre o vestido, usando o histórico.",
    ),
    EvalCase(
        # Mesma observação de "sem corte de relevância" do caso de frete
        # acima — catálogo não vazio sempre entra no prompt.
        id="troca_nao_e_intencao_de_compra",
        question="Como faço para trocar um produto que já comprei?",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=False,
        expect_retrieval=True,
        criterio_qualidade="Pós-venda não é a mesma coisa que fechar uma compra nova — não deveria escalar pro WhatsApp como se fosse uma compra nova.",
    ),
    EvalCase(
        # Limitação CONHECIDA da heurística por palavra-chave (ver
        # revold_ai_assistant.application.use_cases._PURCHASE_INTENT_KEYWORDS): esta
        # pergunta contém "quero comprar" mas é uma dúvida, não uma decisão
        # de compra. expect_escalation=True aqui documenta o comportamento
        # ATUAL (não o ideal) — se um classificador de intenção via LLM
        # substituir a heurística (ver ADR-0011), este caso deveria virar
        # False, e a mudança nesse assert seria o próprio teste de
        # regressão confirmando a melhoria.
        id="duvida_com_palavra_comprar_nao_e_decisao_de_compra",
        question="Será que eu quero comprar isso mesmo, ou tá caro demais pro meu bolso?",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=True,
        expect_retrieval=True,
        criterio_qualidade="Idealmente reconheceria que é uma dúvida, não uma decisão — mas hoje escala mesmo assim (limitação conhecida da heurística por palavra-chave).",
    ),
    EvalCase(
        id="intencao_de_compra_fechar_pedido",
        question="Adorei, quero fechar pedido do jeans reto.",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=True,
        expect_retrieval=True,
        criterio_qualidade="Deve direcionar para o WhatsApp, mesma checagem da frase-gatilho 'fechar pedido'.",
    ),
    EvalCase(
        id="intencao_de_compra_como_pago",
        question="Perfeito, como pago pela blusa de tricô?",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=True,
        expect_retrieval=True,
        criterio_qualidade="Deve direcionar para o WhatsApp, mesma checagem da frase-gatilho 'como pago'.",
    ),
    EvalCase(
        id="intencao_de_compra_quero_fazer_o_pedido",
        question="Show, quero fazer o pedido então.",
        catalog=_CATALOGO_PADRAO,
        expect_escalation=True,
        expect_retrieval=True,
        criterio_qualidade="Deve direcionar para o WhatsApp, mesma checagem da frase-gatilho 'quero fazer o pedido'.",
    ),
    EvalCase(
        # _RETRIEVAL_LIMIT em use_cases.py é 3 — com 5 produtos no índice, a
        # busca nunca deveria devolver mais que 3, senão o system prompt do
        # LLM fica maior que o previsto (custo/latência) sem ninguém notar.
        id="multiplos_produtos_respeita_limite_de_recuperacao",
        question="O que vocês têm disponível na loja toda?",
        catalog=(
            _VESTIDO,
            _CALCA,
            _BLUSA,
            IndexedProduct(sku="SAI-001", name="Saia Midi Plissada", description="Saia midi plissada"),
            IndexedProduct(sku="SHO-001", name="Short de Alfaiataria", description="Short de alfaiataria"),
        ),
        expect_escalation=False,
        expect_retrieval=True,
        criterio_qualidade="Deve mencionar alguns produtos sem tentar listar o catálogo inteiro de uma vez.",
    ),
)
