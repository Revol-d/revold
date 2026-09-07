# ADR-0022: Processo padrão de seed semântico (`make seed`) e módulo `revold_seed`

**Status:** Aceito

## Contexto

Você perguntou como estava o processo de seed, observando corretamente que um site sem banco de dados não dá pra avaliar se está bom — e pediu pra eu estabelecer um processo padrão pra essa parte, que o resultado precisava ser um seed "semântico" (apresentável pra Nick), e pra eu avaliar se fazia sentido um módulo de seed dedicado, dado que em escala cada app/core do monorepo poderia ter seu próprio schema de seed que uma IA usasse com facilidade.

### O que já existia (levantamento feito nesta sessão)

Busca por "seed" no repositório inteiro encontrou só dois artefatos, nenhum dos dois um processo padrão de fato:

1. **`apps/storefront/e2e/global-setup.ts`** (ADR-0020) — semeia 1 categoria + 1 produto + 1 variante via chamada HTTP real contra o api-gateway (login `AUTH_PROVIDER=dev`, os mesmos passos que a Nick faria). Idempotente (checa antes de criar, tolera 409). Mas é propositalmente mínimo e com nomes técnicos (`"Camiseta E2E"`, SKU `TSHIRT-E2E`) — existe só pra dar determinismo aos testes Playwright, nunca foi pensado pra ser olhado por um humano avaliando o site.

2. **`tools/testing/src/revold_testing/*_factories.py`** (ADR-0012) — Factory Boy + Faker (`pt_BR`) por core, gerando dado realista mas **aleatório e deliberadamente cheio de caso de borda** (nome com acento/emoji, descrição vazia, preço com centavos quebrados) — o objetivo explícito é exercitar teste automatizado com dado que fixture escrita à mão nunca cobriria. É a ferramenta certa pra o que foi construída, mas o oposto do que se precisa pra uma vitrine: um nome de produto com emoji ou uma descrição vazia não é "conteúdo realista" numa demo pro cliente, é falha de conteúdo.

Não existe `make seed`, nenhum script de seed de desenvolvimento/demo, nenhum módulo dedicado. Confirmado por `grep -rli seed` no repositório inteiro.

### Por que isso é um problema real, não hipotético

Ficou concreto nesta própria sessão: depois de corrigir um bug de container (`docker compose down -v` para renovar um volume anônimo de `node_modules`), o efeito colateral foi apagar também o volume nomeado do Postgres — e a storefront passou a mostrar a home vazia (a seção de produtos some, pela degradação graciosa recém-implementada) e o erro 500 relatado em `/api/catalog/products` na tela de coleção. Isto não foi um bug de código: foi um banco vazio, sem nenhum caminho padronizado pra repovoar. Qualquer `make clean`, ambiente novo, ou banco recriado deixa o site nesse mesmo estado.

## Decisão

### 1. `make seed`: processo padrão, único, idempotente

Novo alvo `make seed` (`docker compose run --rm api-gateway poetry run python -m revold_seed`) — roda depois de `make migrate` num banco vazio (ou a qualquer momento; é seguro repetir) e deixa o storefront/admin-dashboard com um catálogo coerente: 6 categorias, 21 produtos com 2-4 variantes cada, preços/descrições/tamanhos/cores plausíveis para uma loja de roupa em português, mais a configuração da loja (`/configuracoes`) preenchida — tudo escrito à mão, sem Faker.

Regras de idempotência (por construção, não por sorte):
- **Categoria/produto**: só cria se ainda não existir (checa por slug/SKU). Rodar de novo depois que a Nick já editou algo semeado no admin **não desfaz a edição dela** — isto é seed de baseline, não sincronização contínua.
- **Estoque**: só entra a diferença até a quantidade-alvo (nunca reduz, nunca duplica) — `ReceiveStock` é aditivo por natureza (`core_inventory.use_cases.ReceiveStock`), então checar antes é obrigatório pra poder rodar `make seed` mais de uma vez sem dobrar o estoque a cada execução.
- **Configuração da loja**: só grava se ainda não houver nenhum registro — depois que a Nick preencher CNPJ/contato de verdade, `make seed` nunca mais toca nesse registro.

Persistência sempre via os repositórios reais (`PostgresProductRepository`, `PostgresInventoryRepository`, `PostgresStoreSettingsRepository`) e os mesmos objetos de domínio (`core_catalog.domain.Product`, etc.) que uma chamada de admin real geraria — nunca `INSERT` cru. As invariantes de domínio (`Money` não aceita negativo, `StoreSettings` valida CNPJ/e-mail) continuam valendo automaticamente. Mesmo raciocínio que já justificava o `global-setup.ts` semear via HTTP em vez de SQL — aqui é direto contra o repositório (mais rápido, sem precisar de servidor/login, já que é uma tarefa de desenvolvimento interna, não uma simulação de ação da Nick).

Conteúdo deliberadamente variado pra exercitar o que já está implementado: produtos com `original_price` (preço promocional), uma variante com `in_stock=False` (mostra "esgotado" no storefront), duas variantes com estoque físico abaixo do `low_stock_threshold` configurado (mostra o alerta de estoque baixo em `/estoque` sem precisar vender nada primeiro), imagens via `picsum.photos` com seed determinístico por SKU (nunca fica com espaço em branco no lugar da foto — troque pelo upload real assim que a Nick tiver fotos, ver `MediaStorage`).

### 2. Módulo de seed dedicado: `tools/seed` (pacote `revold_seed`) como orquestrador fino + `seed.py` por core

Sim, faz sentido — e o desenho segue precedente que já existe no repositório em vez de inventar um novo:

- **`tools/testing`** já é o precedente de "ferramenta compartilhada entre cores, fora de qualquer core individual" — `tools/seed` é o mesmo tipo de pacote, com o mesmo motivo de existir fora de `cores/`.
- **Conteúdo do dado fica DENTRO de cada core**, não no orquestrador: `cores/core-catalog/src/core_catalog/seed.py` (`CATEGORIES`, `PRODUCTS`) e `cores/core-store-settings/src/core_store_settings/seed.py` (`DEMO_SETTINGS`). Isto segue o mesmo princípio de isolamento entre cores da ADR-0002 — só `core_catalog` sabe o que é um catálogo semanticamente válido, só `core_store_settings` sabe o que é um registro de configuração preenchido; um orquestrador central que soubesse o conteúdo de todo mundo violaria exatamente o isolamento que o resto do repositório mantém.
- **`tools/seed/src/revold_seed/runner.py`** só conhece a ORDEM de dependência entre cores (categoria → produto → estoque → configuração da loja) e como persistir cada um através do repositório dele — nunca o conteúdo em si.
- **Contrato de extensão, pensado explicitamente para IA a operar** (o ponto que você levantou sobre escala): um core novo que precise de seed no futuro só escreve o próprio `seed.py` no mesmo formato — dataclasses de domínio do próprio core, ou uma dataclass "Seed*" auxiliar quando o core precisa de um campo que só faz sentido no momento do seed (ex. `SeedVariant.initial_stock`, que não existe em `ProductVariant` porque `core_catalog` não conhece estoque) — e registra uma função `_seed_<nome>` no orquestrador. Uma IA instruída a "adicionar seed pro core X seguindo o padrão de `core_catalog/seed.py`" tem exatamente o formato esperado sem precisar entender nenhum framework de seed novo — é o mesmo raciocínio de "provider-swap via env var" e "core pequeno centralizado" já usados no projeto: convenção simples e replicável em vez de abstração genérica.

`pyproject.toml` ganhou `{ include = "revold_seed", from = "tools/seed/src" }` em `[tool.poetry.packages]` — nenhuma mudança no `Dockerfile` do api-gateway foi necessária: `COPY tools ./tools` (adicionado na ADR-0021) já copia qualquer coisa nova sob `tools/`, incluindo este pacote.

## Consequências

- `make seed` depois de `make migrate` é agora o passo padrão documentado (`docs/guides/development.md`) pra qualquer avaliação do storefront/admin-dashboard — inclusive depois de um `make clean`/volume novo, o cenário que expôs o problema nesta sessão.
- O seed nunca sobrescreve dado real editado pela Nick — é seguro rodar a qualquer momento em qualquer ambiente (dev, ou futuramente um ambiente de demo/staging), inclusive repetidamente, sem risco de duplicar produto, dobrar estoque ou apagar uma configuração já preenchida.
- Conteúdo do seed (nomes, preços, descrições) é o primeiro rascunho de catálogo pra apresentar pra Nick — esperado que ela queira ajustar nomes/preços reais assim que tiver fotos e catálogo definitivos; o objetivo aqui é nunca mais ter que avaliar o site vazio, não substituir o catálogo real dela.
- Este processo não interfere com `tools/testing` (fábricas de Faker continuam sendo a ferramenta certa para teste automatizado) nem com `apps/storefront/e2e/global-setup.ts` (que continua existindo, escopado só pro que os testes E2E precisam) — os três coexistem com propósitos diferentes e não deveriam convergir num só.
- Validado de ponta a ponta nesta sessão — não só por leitura de código. Este ambiente de sandbox já tinha um Postgres 16 instalado via apt (ver ADR anterior sobre a mesma técnica, usada porque Docker Hub é bloqueado aqui) com as migrações já aplicadas e um produto/categoria/configuração de loja de uma sessão de diagnóstico anterior — cenário melhor que um banco vazio pra validar de verdade a idempotência: rodei `python -m revold_seed` (fora de Docker, `PYTHONPATH` apontando direto pros `src` de cada pacote, sem precisar do `poetry install` completo) contra esse banco com dado pré-existente.
  - **1ª execução**: criou as 5 categorias que faltavam (a 6ª, `camisetas`, já existia — o script corretamente reconheceu e reaproveitou), os 21 produtos declarados, 47 variantes, 45 entradas de estoque; reconheceu a configuração da loja pré-existente e não tocou nela.
  - **2ª execução (imediata, mesmo banco)**: `0` em toda categoria — confirma que rodar `make seed` de novo não duplica nada.
  - Consultado o Postgres diretamente depois: as 2 variantes marcadas `in_stock=False` no seed (`CAM-004-G-CINZA`, `CAL-004-40-VERDE`) estão `false` no banco; as 2 variantes com `initial_stock` abaixo do limiar (`VES-003-P-BEGE`: 3, `CAD-003-36-DOURADO`: 2) estão com exatamente essa quantidade em `inventory_stock_levels`; os 3 produtos com `original_price` (`CAM-002`, `VES-002`, `JAQ-002`) gravaram os dois preços corretamente.
  - Não validado neste ambiente: rodar via `docker compose run --rm api-gateway ...` em si (mesma limitação de Docker Hub bloqueado das ADRs 0020/0021) — só o comportamento do script em si, que é idêntico dentro do container (mesmo `DATABASE_URL`, mesmo código, mesmo `python -m revold_seed`). Se `make seed` falhar por algum motivo específico de container (variável de ambiente ausente, rede), o erro deve apontar exatamente pra isso — o script não engole exceção silenciosamente.
