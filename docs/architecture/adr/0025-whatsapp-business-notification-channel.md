# ADR-0025: canal de notificação por WhatsApp Business — automação de aviso à Nick, não do checkout do cliente

**Status:** Aceito

## Contexto

Onda 7 do plano em `claude/planejamento-pagamentos-e-comunicacao-avancada.md`:
depois de `core-orders` (ADR-0023) e `core-payments` (ADR-0024), faltava o
outro gap original — notificação por WhatsApp automatizada, hoje só
existente como link de clique-para-conversar (ADR-0005). O plano previa
duas mudanças:

1. `NotificationChannel` (`core-notification`) ganha
   `WhatsAppBusinessNotificationChannel` — avisos assíncronos
   (`checkout.created`, `stock.low`) por WhatsApp em vez de e-mail/log.
2. `CheckoutHandoff` (`core-communication`) ganha uma segunda
   implementação, `whatsapp-business-api`, para "confirmação de pedido"
   automatizada.

## Decisão

**Item 1 (canal de notificação) implementado por completo.**
`WhatsAppBusinessNotificationChannel` fala com a Meta Cloud API
(`POST https://graph.facebook.com/v20.0/{phone_number_id}/messages`) para
avisar a Nick — mesmo destinatário que já usa `NICK_WHATSAPP_NUMBER`
(ADR-0005), então não há dado novo para coletar. Seleção via
`NOTIFICATION_PROVIDER=whatsapp-business` (mesmo padrão de
`NOTIFICATION_PROVIDER=smtp`, ADR-0018), consumido pelo
`workers/event-worker` (que já é quem despacha `checkout.created`/
`stock.low` de forma assíncrona, ADR-0013) — nenhuma mudança na porta nem
em quem a usa.

**Limitação real da própria API do WhatsApp, documentada no adapter:**
fora da janela de 24h de conversa, a Meta só aceita mensagem de **template
pré-aprovado**, não texto livre. O adapter manda `type: text` por padrão
(funciona no número de teste, onde a Nick pode iniciar a janela mandando
uma mensagem primeiro) e aceita `WHATSAPP_BUSINESS_TEMPLATE_NAME` opcional
para quando houver um template aprovado em produção.

**Item 2 (CheckoutHandoff automatizado) NÃO implementado nesta onda —
decisão sua pendente, não esquecimento:**

## Decisão pendente: automatizar o handoff de checkout exige capturar o telefone do cliente

O clique-para-conversar (ADR-0005) funciona hoje **sem nenhum dado do
cliente**: o próprio navegador dele abre o WhatsApp com uma mensagem
pré-preenchida, endereçada ao número da Nick. Uma segunda implementação de
`CheckoutHandoff` que *automatiza* esse envio (nosso backend manda a
mensagem, em vez do cliente) precisaria mandar essa mensagem **para o
WhatsApp do cliente** — e isso exige um número de telefone do cliente que
**não é coletado em lugar nenhum do checkout hoje** (é, inclusive, o que
permite o checkout ser tão simples: sem conta, sem formulário).

Não implementei isso adivinhando a resposta, pelo mesmo motivo de outras
decisões que ficaram registradas como pendentes neste projeto (ex.:
`claude/status-implementacao.md`, "não assumi sozinho onde a Nick
gostaria de ver os dados de configuração da loja"). As opções reais são:

1. **Adicionar um campo de telefone no checkout** (`core-cart` ou
   `core-orders`) — muda o formulário que o cliente preenche hoje, ganho
   real (a Nick recebe e o cliente também recebe confirmação automática),
   mas é uma mudança de UX, não só técnica.
2. **Manter só o clique-para-conversar para o cliente**, e usar
   `WhatsAppBusinessNotificationChannel` (item 1, já pronto) só para
   avisar a Nick — o cliente confirma pelo mesmo link de sempre. É o que
   está em produção agora, sem mudança nenhuma de UX.
3. Alguma combinação (ex.: campo de telefone opcional, só para quem quiser
   confirmação automática).

Fico aguardando sua decisão para desenhar a Onda 7 "completa"; enquanto
isso, o item 1 já entrega o valor de ter aviso automático por WhatsApp
para a Nick, que é metade real do gap original.

## Sobre a validação

Mesmo padrão de ADR-0024/ADR-0012: testes `respx` (`adapters/external/
tests/test_whatsapp_business_channel.py`) simulam o formato documentado
publicamente da Meta Cloud API — não existe emulador oficial, então isto
confere que o adapter segue a documentação, não que a API real se
comporta exatamente assim. A validação final precisa de um número de
teste + `access_token` da Meta (Cloud API libera isso sem aprovação
completa de negócio, até 5 destinatários verificados) — só o Samuel pode
gerar essa credencial.

## Consequências

- `checkout.created`/`stock.low` podem ser avisados por WhatsApp em vez
  de só log/e-mail, com `NOTIFICATION_PROVIDER=whatsapp-business` — zero
  mudança de código quando a credencial existir, mesmo princípio de
  `AUTH_PROVIDER`/`PAYMENT_PROVIDER`/`LLM_PROVIDER`.
- **Bug real encontrado e corrigido ao configurar isto**:
  `docker-compose.yml` tinha `NOTIFICATION_PROVIDER: logging` fixado em
  `environment:` tanto no `api-gateway` quanto no `worker` — isso tem
  prioridade sobre o `.env` no Compose, então `NOTIFICATION_PROVIDER=smtp`
  (ADR-0018, já existia) ou `=whatsapp-business` (esta rodada) no `.env`
  **nunca tinha efeito rodando via `make dev`**, silenciosamente. Ninguém
  tinha notado porque o canal SMTP nunca tinha sido testado de ponta a
  ponta via Compose. Corrigido removendo o valor fixo das duas
  `environment:` — o default (`logging`) continua vindo do `.env.example`.
- **Gap também encontrado e corrigido**: `PAYMENT_PROVIDER`/
  `MERCADO_PAGO_*` (ADR-0024, onda anterior) nunca tinham sido adicionados
  ao `.env.example` — ficavam sem nenhuma documentação de como configurar.
  Corrigido nesta rodada.
- `CheckoutHandoff` continua com uma implementação só
  (`whatsapp-clicktochat`) — nenhuma mudança de comportamento para o
  cliente até a decisão acima ser tomada.

## Validação

Ver `claude/status-implementacao.md` (rodada correspondente).
