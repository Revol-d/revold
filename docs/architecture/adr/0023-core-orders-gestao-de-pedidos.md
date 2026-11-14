# ADR-0023: `core-orders` — pedido persistido como pré-requisito de pagamento

**Status:** Aceito

## Contexto

Bati a simulação "Anatomia da Escala" (estudo de reuso de leafs de plataforma
contra 3 clientes hipotéticos) contra o código real do Nick e encontrei dois
gaps que Samuel já esperava: notificação automática por WhatsApp e pagamento
Pix/cartão (nenhum dos dois existe em código — ver
`claude/planejamento-pagamentos-e-comunicacao-avancada.md`). Ao desenhar o
pagamento, apareceu um terceiro gap, mais fundamental: **não existe conceito
de pedido persistido**. Hoje (ADR-0005), o checkout é efêmero — o carrinho
vira um link `wa.me` e nada fica gravado do lado do Nick; a conciliação é
100% manual, na cabeça dela. Isso já era um gap conhecido ("Gestão de
pedidos no admin: ❌ não implementado" em `claude/status-implementacao.md`),
mas virou bloqueante agora: pagamento precisa de algo persistido para
amarrar "cobrança confirmada" a "estes itens, deste carrinho".

## Decisão

Novo core pequeno, `core-orders`, seguindo o mesmo padrão hexagonal dos
demais (`core-store-settings`, `core-events`): domínio próprio (`Order`,
`OrderLine`, `Money` — não importa `core_cart.domain.Money` nem
`core_catalog.domain.Money` de propósito, ADR-0002), porta
`OrderRepository`, casos de uso, adapter Postgres real.

**Quando o pedido é criado:** dentro do checkout do carrinho
(`api_gateway.routers.cart.start_checkout`), depois que o handoff do
WhatsApp já foi montado com sucesso e o estoque já foi reservado de
verdade — não antes, para não registrar uma tentativa que nunca saiu do
carrinho. A tradução `Cart` (core-cart) → `OrderLine` (core-orders)
acontece no api-gateway, que é quem já orquestra os dois cores hoje (a
mesma camada que traduz `Cart` → `CartSummary` para o `CheckoutHandoff`).

**Confirmação de pagamento nesta onda ainda é manual**, por decisão
(ADR-0005 continua valendo: sem CNPJ, sem gateway formal). A Nick confere
o pagamento pelo WhatsApp e marca o pedido como pago em `/pedidos`
(admin-dashboard), via `PATCH /api/orders/{id}/payment-status`. Quando
`core-payments` (próxima onda) existir, um webhook do gateway chama os
**mesmos casos de uso** (`MarkOrderPaid`) — o endpoint/UI atuais não
precisam mudar, só ganham um segundo chamador automático.

**Transições de status são uma máquina de estados simples, validada no
domínio** (`Order.mark_paid/cancel/mark_shipped/mark_delivered`):
cancelamento só é permitido antes da confirmação de pagamento (cancelar um
pedido já pago é estorno — fora de escopo aqui, fica para `core-payments`);
envio exige pagamento confirmado; entrega exige envio prévio. Uma
transição inválida levanta `InvalidOrderTransition` → HTTP 422.

**Persistência:** tabelas `orders` (um registro por pedido) e
`order_lines` (FK para `orders`, cascade delete-orphan) — mesmo padrão
relacional de `catalog_products`/`catalog_product_variants`, não um JSON
solto, para manter a mesma convenção de todo o resto do catálogo. As
linhas só são gravadas na criação; chamadas de `save()` seguintes (por
transição de status) não as tocam.

**RBAC:** `GET /api/orders/{id}` não exige papel — `order_id` funciona
como token de capacidade, mesmo padrão de `cart_id` (o cliente acompanha o
próprio pedido sem precisar de conta). Listagem e transições de status
exigem STAFF/ADMIN, mesmo nível de `core-inventory`.

## Consequências

- Fecha, por si só, o gap "gestão de pedidos no admin" que estava na
  tabela de requisitos funcionais há duas rodadas — tela `/pedidos` nova.
- Todo checkout a partir de agora grava um pedido; carrinhos abertos antes
  desta mudança nunca tiveram pedido (não há migração de dados histórica —
  não existia o que migrar).
- `CheckoutHandoffResponseSchema` (contrato de `core-cart`) ganhou o campo
  `order_id` — mudança aditiva, não quebra nenhum consumidor existente
  (nenhum front hoje lia esse campo, mas nenhum también dependia da forma
  exata do schema).
- Pré-requisito direto da próxima onda (`core-payments`, ADR-0024): o
  webhook do gateway de pagamento vai chamar `MarkOrderPaid`/`CancelOrder`
  por `order_id`.
- **Limitação deliberada desta onda:** não há reserva de estoque
  "definitiva" amarrada ao pedido — a baixa de fato continua acontecendo
  como hoje (reserva no checkout, confirmação manual pela Nick fora do
  sistema). Isso só muda quando `core-payments` existir e `order.paid`
  (evento) puder disparar a baixa real.
- **Não implementado nesta onda:** fábrica de dados (`revold_testing`)
  para `core-orders` — pode ser adicionada depois, mesmo padrão dos outros
  cores, sem urgência (o backlog já registra isso para os cores mais
  recentes).

## Validação

Ver `claude/status-implementacao.md` (rodada correspondente) para o
resultado real de rodar a suíte completa e os testes de integração contra
Postgres.
