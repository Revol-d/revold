# ADR-0024: `core-payments` — cobrança Pix real, cartão deliberadamente adiado

**Status:** Aceito

## Contexto

`core-orders` (ADR-0023) resolveu o pré-requisito de ter um pedido
persistido. Falta o gap original que motivou a onda inteira: hoje não
existe nenhuma forma de cobrar o cliente por Pix ou cartão — a Nick recebe
o pagamento fora do sistema (Pix manual, maquininha própria) e confirma na
mão em `/pedidos`. `claude/planejamento-pagamentos-e-comunicacao-avancada.md`
já mapeava o Mercado Pago como gateway (CNPJ do Nick já cadastrado lá,
segundo o Samuel) e apontava uma decisão pendente sobre o fluxo de cartão
(Checkout Pro vs. Payment Brick, parcelamento) que não bloqueia Pix.

## Decisão

Novo core, `core-payments`, mesmo padrão hexagonal: domínio próprio
(`Charge`, `Money`, `PaymentMethod`, `ChargeStatus` — não importa
`core_orders.domain.Money` de propósito, ADR-0002), portas
(`PaymentGateway`, `ChargeRepository`), casos de uso, dois adapters de
gateway (`FakePaymentGateway` para dev/teste, `MercadoPagoGateway` real) e
persistência Postgres.

**Escopo desta onda: só Pix está implementado de fato contra o Mercado
Pago.** `MercadoPagoGateway.create_charge` levanta `NotImplementedError`
para `PaymentMethod.CREDIT_CARD` — não é um placeholder esquecido, é
decisão: cartão precisa que o Samuel decida entre checkout hospedado
(Checkout Pro, mais simples, redireciona o cliente) e tokenização
client-side (Payment Brick, fica na nossa página, mas exige o SDK JS do
Mercado Pago no storefront e uma decisão sobre parcelamento) — implementar
qualquer um dos dois sem essa decisão arrisca ter que refazer a
reconciliação de webhook depois. `FakePaymentGateway` (dev) segue
suportando os dois métodos, então a lacuna de cartão não bloqueia
desenvolvimento local.

**PCI-DSS:** o cartão em si nunca deve ser processado nem armazenado no
nosso backend, independente de qual dos dois fluxos acima o Samuel
escolher — ambos existem justamente para isso (checkout hospedado ou
tokenização feita pelo SDK do Mercado Pago direto no navegador do
cliente). Isso é um requisito do desenho, não um detalhe de implementação
adiável.

**Confirmação nunca confia no payload do webhook.** O Mercado Pago assina
o webhook com um esquema próprio (header `x-signature` no formato
`ts=<epoch>,v1=<hmac-hex>`, header `x-request-id`, query param `data.id`;
manifesto `id:{data_id};request-id:{request_id};ts:{ts};` em HMAC-SHA256
com o segredo da conta) — `verify_webhook_signature` valida isso antes de
qualquer coisa. Mesmo depois de validada a assinatura,
`ConfirmChargeFromWebhook` reconsulta o status real via
`get_charge_status` em vez de confiar no que o payload alega, e é
idempotente (um webhook duplicado numa cobrança que não está mais PENDING
simplesmente devolve a cobrança como está, sem reprocessar).

**Idempotência na criação:** `CreateCharge` reaproveita uma cobrança
PENDING existente do mesmo pedido em vez de abrir uma segunda no gateway —
evita cobrança duplicada se o cliente clicar "pagar" mais de uma vez antes
do primeiro Pix expirar.

**Ponte cross-core vive no api-gateway** (`api_gateway.routers.payments`),
nunca dentro de `core-payments` nem `core-orders` (ADR-0002): o endpoint de
criação de cobrança lê o pedido (`core-orders`) para saber o valor a
cobrar; o webhook, depois de confirmar a cobrança como paga, chama
`MarkOrderPaid` (`core-orders`) pelo `order_id` guardado na própria
`Charge` — o mesmo caso de uso que a Nick aciona manualmente hoje em
`/pedidos` (ADR-0023), sem duplicar lógica de transição de estado.

**Sem RBAC** em `POST/GET /api/orders/{order_id}/charges`, mesmo
raciocínio de `GET /api/orders/{order_id}`: `order_id` já funciona como
token de capacidade, e é o próprio cliente (não a Nick) quem abre e
acompanha a cobrança do pedido dele.

**Seleção de provedor via `PAYMENT_PROVIDER`** (`fake` por padrão,
`mercado_pago` quando configurado — mesmo padrão de
`AUTH_PROVIDER`/`MEDIA_STORAGE_PROVIDER`/`LLM_PROVIDER`): sem as três env
vars do Mercado Pago (`MERCADO_PAGO_ACCESS_TOKEN`,
`MERCADO_PAGO_WEBHOOK_SECRET`, `MERCADO_PAGO_PAYER_EMAIL`) configuradas, a
factory levanta `NotImplementedError` em vez de deixar o servidor subir
com um provedor real mal configurado.

## Sobre a validação do adapter do Mercado Pago

Os testes de `MercadoPagoGateway` usam `respx` para interceptar as
chamadas HTTP que o adapter faz via `httpx`, simulando os formatos de
request/response documentados publicamente pela API do Mercado Pago —
mesmo padrão já usado para o Azure OpenAI (ADR-0012). **Isto é
deliberadamente diferente** de Azurite (`test_azure_blob_storage.py`) ou
aiosmtpd (`test_smtp_channel.py`): aqueles são emuladores oficiais que
falam o protocolo de verdade; não existe equivalente para o Mercado Pago.
Os testes aqui validam que o adapter monta a requisição certa e interpreta
a resposta certa **segundo a documentação**, não contra o comportamento
real do gateway. A validação real só acontece com um `access_token` de
teste do Mercado Pago, que só o Samuel pode gerar (é uma credencial de
conta) — até lá, esta é a melhor cobertura possível a partir daqui.

## Consequências

- Fecha o gap "pagamento Pix/cartão: ❌ não implementado" para a parte Pix;
  cartão fica documentado como decisão pendente, não como esquecimento.
- `/pedidos` (admin-dashboard) continua funcionando exatamente como
  ADR-0023 deixou — a confirmação manual pela Nick não foi removida,
  porque cartão ainda depende dela e porque é um fallback razoável se o
  webhook falhar por qualquer motivo.
- Tabela nova, `payment_charges`, independente de `orders` (só referencia
  `order_id` frouxamente, sem FK — mesmo padrão de referência solta entre
  bounded contexts já usado em `orders.cart_id`).
- **Não implementado nesta onda:** cobrança de cartão via Mercado Pago
  (bloqueado por decisão de UX/parcelamento do Samuel); estorno
  (`Charge.mark_refunded` já existe no domínio, mas nenhum caso de uso
  público chama); reconciliação por polling para o caso de o webhook nunca
  chegar (hoje só o webhook confirma; ficaria pendente até a Nick conferir
  manualmente); **UI no storefront** — os endpoints (`POST/GET
  /api/orders/{id}/charges`) existem e estão testados, mas nenhuma tela do
  storefront ainda chama "criar cobrança" nem exibe QR code/copia-e-cola,
  nem dá polling no status — isso é trabalho de frontend que só faz
  sentido com uma conta real do Mercado Pago para testar de ponta a ponta
  (`PAYMENT_PROVIDER=fake` cobre o backend, mas uma tela de Pix sem Pix de
  verdade por trás tem pouco valor de validação).
- **Ponte com estoque, adicionada nesta onda:** `FulfillReservedStock`
  (`core-inventory`) existia desde antes, sem nenhum chamador —
  ADR-0023 registrava isso como limitação deliberada. Agora tanto a
  confirmação manual (`PATCH /api/orders/{id}/payment-status`,
  `mark_paid`) quanto o webhook do Mercado Pago chamam
  `api_gateway.orchestration.fulfill_order_stock` ao confirmar pagamento,
  dando baixa definitiva (não só reserva) no estoque de cada linha do
  pedido. Uma inconsistência aqui (SKU sem registro, reserva insuficiente)
  fica só logada — não reverte o pagamento já confirmado.
- Pré-requisito indireto da Onda 7 (WhatsApp Business API,
  `claude/planejamento-pagamentos-e-comunicacao-avancada.md`): quando essa
  onda existir, a confirmação de pagamento (manual ou via webhook) pode
  disparar uma notificação automática ao cliente pelo mesmo canal.

## Validação

Ver `claude/status-implementacao.md` (rodada correspondente) para o
resultado real de rodar a suíte completa e os testes de integração contra
Postgres.
