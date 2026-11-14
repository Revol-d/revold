"""Núcleo de domínio de pedidos (ADR-0023).

Registra o que acontece com um carrinho depois do checkout — hoje o
handoff de checkout (ADR-0005) é efêmero: o carrinho vira um link do
WhatsApp e nada fica gravado do lado do Nick. `core-orders` fecha essa
lacuna (já registrada como "Gestão de pedidos no admin: não implementado"
em claude/status-implementacao.md) e é o pré-requisito de `core-payments`
(onda seguinte): pagamento precisa de algo persistido para amarrar
"cobrança paga" a "estes itens, deste carrinho".
"""
