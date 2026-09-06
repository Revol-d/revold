# ADR-0020: Testes E2E com Playwright

**Status:** Aceito

## Contexto

O `Readme.md` define a pirâmide de testes (Unit 70% / Integration 20% / E2E 5%) e o `Makefile` já tinha um alvo `test-e2e` (`docker compose run --rm storefront pnpm exec playwright test`) desde o início do projeto — mas nenhum arquivo de teste E2E jamais existiu. O `package.json` do storefront tinha só um placeholder (`echo "(e2e via playwright, ver Makefile test-e2e)"`) no lugar do teste de verdade. `claude/status-implementacao.md` documentava isso como lacuna conhecida desde a primeira avaliação macro do projeto.

## Decisão

**Playwright**, cobrindo o fluxo real de cliente ponta a ponta (o mesmo que `claude/status-implementacao.md` já previa como prioridade: "navegar → adicionar ao carrinho → WhatsApp") contra o storefront + api-gateway + Postgres/Redis **reais**, sem mockar nada:

- `apps/storefront/playwright.config.ts`: um projeto Chromium, `executablePath` apontando pro binário já instalado no ambiente (`PLAYWRIGHT_BROWSERS_PATH`) em vez de deixar o Playwright baixar um binário — importante em qualquer ambiente com egress restrito.
- `apps/storefront/e2e/global-setup.ts`: semeia uma categoria + produto + variante + estoque via chamadas HTTP reais ao api-gateway (login `AUTH_PROVIDER=dev`, que já dá papel ADMIN instantâneo em ambiente de desenvolvimento — ver `dev_provider.py`) — os mesmos passos que a Nick faria pelo admin-dashboard, não um insert direto no banco. Idempotente (tolera re-execução).
- `apps/storefront/e2e/checkout.spec.ts`: dois testes —
  1. navega pela coleção → abre o produto → adiciona ao carrinho → fecha o pedido pelo WhatsApp → confirma que a resposta da API de checkout (`handoff_url`) contém a URL `wa.me` certa com o produto certo (ADR-0005). O conteúdo da mensagem vem da própria API, não da página do WhatsApp carregar de verdade — isso mantém o teste determinístico em qualquer ambiente, com ou sem rota de saída pra `wa.me` (o popup em si é conferido separadamente, confirmando que `window.open` foi de fato chamado).
  2. busca por nome do produto semeado, exercitando a busca full-text (ADR-0014) de ponta a ponta, não só a query isolada do repositório.
- `Makefile` (`test-e2e`) e `apps/storefront/Dockerfile` (stage `dev`, que é o usado por `docker compose run --rm storefront ...`): adicionado `pnpm exec playwright install --with-deps chromium` no build da imagem de dev, senão `node:20-slim` não tem Chromium nem as libs de sistema pra rodar headless.

## Achados reais ao implementar (não hipotéticos — encontrados rodando contra um browser de verdade)

Nenhum destes apareceria em teste de unidade/contrato (que não usam browser nem Docker Compose de verdade):

1. **`docker-compose.yml` não carregava `.env` nos containers de `api-gateway`/`worker`.** Nenhum serviço tinha `env_file`, então qualquer variável do `.env.example` que não estivesse hardcoded em `environment:` no compose (`NICK_WHATSAPP_NUMBER`, `SESSION_COOKIE_SECURE`, `SMTP_*`, `AZURE_*`, `GOOGLE_*` etc.) nunca chegava ao container — `cp .env.example .env` (passo 1 do guia de desenvolvimento) preenchia um arquivo que o Compose simplesmente ignorava. Corrigido com `env_file: [.env]` em `api-gateway` e `worker` (`environment:` continua tendo prioridade pras mesmas chaves).
2. **`SESSION_COOKIE_SECURE=true` por padrão quebrava login em `make dev`.** O `docker-compose.yml` deste repositório não tem HTTPS em lugar nenhum (sem proxy reverso/certificado — ADR-0009 é sobre Docker, não sobre TLS local). Com o cookie de sessão `Secure=true` e o storefront/admin-dashboard servidos em HTTP puro, o navegador descartava o cookie silenciosamente — login "funcionava" (200 OK, corpo com o usuário) mas a sessão nunca persistia de fato. `.env.example` corrigido pra `SESSION_COOKIE_SECURE=false` (produção em Container Apps, com HTTPS de verdade, deve usar `true`).
3. **Corrida de hidratação client-side.** Clicar num botão de Client Component (`AddToCartButton`) imediatamente após a navegação pode acontecer antes do React hidratar e ligar o `onClick` — o HTML de SSR já mostra o botão como habilitado, mas o clique nesse instante é um no-op. O teste espera `networkidle` antes de interagir.
4. **Banner de cookies intercepta clique em elemento atrás dele.** `ConsentBannerContainer` fixo na base da tela bloqueava clique no botão de checkout do drawer do carrinho (que abre por cima dele) — Playwright detectou e recusou o clique (`intercepts pointer events`), o que um teste rodando sem verificação de sobreposição real (ou um clique programático via `dispatchEvent`) nunca pegaria. O teste passou a descartar o banner primeiro, como um visitante real faria.

## Consequências

- Fecha a lacuna de E2E que `Makefile`/`Readme.md` já prometiam — `make test-e2e` agora roda teste de verdade, não um comando vazio.
- Achados 1 e 2 acima eram bugs reais de configuração local, não relacionados a este ADR em si — corrigidos junto porque bloqueavam qualquer teste E2E via browser de funcionar (e bloqueariam qualquer humano tentando `make dev` + login pela primeira vez).
- Este ambiente de implementação (sandbox de nuvem) não tem Docker funcional (Docker Hub bloqueado) nem saída de rede pra `wa.me` — a suíte foi validada rodando os processos nativamente (Postgres/Redis já instalados via apt, `poetry run uvicorn` + `pnpm dev` diretamente, sem compose) e o teste foi desenhado para não depender de `wa.me` responder de verdade. Em uma máquina real com Docker (Windows do Samuel, CI), `make test-e2e` deve funcionar sem essa adaptação.
- Só um browser (Chromium) e um fluxo coberto por enquanto — cobertura mais ampla (Firefox/WebKit, mais fluxos: wishlist, chat assistente, admin-dashboard) fica como próximo passo natural, não bloqueio.
- `@playwright/test` vira devDependency de `apps/storefront` — só o stage `dev` da imagem Docker paga o custo de baixar Chromium + libs de sistema; o stage `runtime` (produção) não é afetado.
