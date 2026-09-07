# ADR-0021: Reprodução local do CI (`act`) e correção de duas falhas que só apareciam no runner do GitHub Actions

**Status:** Aceito

## Contexto

O primeiro push que efetivamente disparou `.github/workflows/ci.yml` (job `python` e job `node`) falhou nos dois jobs, com dois erros que nunca tinham aparecido em nenhuma rodada de teste anterior nesta sessão de desenvolvimento:

1. **Job `python`** — `poetry run pytest --cov` falhou na *coleta* de 9 arquivos de teste (`test_assistant_routes.py`, `test_cart_routes.py`, `test_catalog_routes.py`, `test_identity_routes.py`, `test_inventory_rbac.py`, `test_inventory_routes.py`, `test_metrics_endpoint.py`, `test_public_api_routes.py`, `test_store_settings_routes.py`) — todos os que fazem `from api_gateway.main import app` — com `PermissionError: [Errno 13] Permission denied: '/app'`.
2. **Job `node`** — `pnpm -r lint` falhou em `packages/ui` com `ESLint: No files matching the pattern "." were found`.

Nenhum dos dois é regressão de código deste ADR ou do anterior — os dois já existiam antes, só nunca tinham sido exercitados nas condições reais do runner do GitHub Actions.

## Causa raiz

### 1. `PermissionError: '/app'`

`apps/api_gateway/src/api_gateway/main.py` (em nível de módulo, executado só de *importar* `api_gateway.main`) e `adapters/external/src/adapters_external/media/factory.py` tinham:

```python
_media_dir = Path(os.environ.get("MEDIA_STORAGE_LOCAL_DIR", "/app/media"))
_media_dir.mkdir(parents=True, exist_ok=True)
```

`/app` só existe porque o `Dockerfile` do api-gateway usa `WORKDIR /app` — e só é gravável lá porque o processo roda como root dentro do container. `docker-compose.yml` sempre setou `MEDIA_STORAGE_LOCAL_DIR=/app/media` explicitamente para os serviços `api-gateway`/`worker`, então o fallback hardcoded nunca tinha sido exercitado em nenhuma rodada anterior — todas rodaram via `make test`/`make lint` (que chamam `docker compose run --rm api-gateway ...`, ADR-0009) ou neste ambiente de sandbox de nuvem, onde o usuário é root e `mkdir /app` simplesmente funciona por acidente (ver "Consequências" abaixo). O job `python` do CI roda `poetry install`/`poetry run pytest` **direto no runner do GitHub Actions** (`ubuntu-latest`, usuário não-root, sem Docker nenhum) — é o único lugar do projeto inteiro que executa nessas condições, e foi o primeiro a expor que o fallback nunca foi seguro fora de um container.

### 2. `ESLint: No files matching the pattern "." were found`

`packages/ui/package.json` tinha `"lint": "eslint . --max-warnings=0"`, sem nenhum `.eslintrc.*` próprio e sem `eslint` nas suas próprias `devDependencies` — o binário resolvido (ESLint 8.57.1, confirmado no log) só existia porque o pnpm workspace faz *hoist* do `eslint` declarado em `apps/storefront`/`apps/admin-dashboard`. Sem config própria e sem `--ext`, o ESLint 8 (config legada, não flat config) só considera `.js` por padrão — `packages/ui/src` só tem `.ts`/`.tsx` — daí "nenhum arquivo corresponde ao padrão". Isso também nunca tinha rodado de verdade antes: `make lint` chama `pnpm lint` só dentro do container `storefront` (que não inclui `packages/ui` no `pnpm -r`), e o `ci.yml` foi o primeiro a rodar `pnpm -r lint` na raiz do monorepo de verdade.

### O padrão comum aos dois

O projeto segue à risca a ADR-0009 ("todo comando roda em Docker") para o fluxo de desenvolvimento — mas os alvos do `Makefile` (`make test`, `make lint`, `make coverage`) rodam **dentro dos containers da aplicação** (`docker compose run --rm api-gateway ...`), nunca nas condições do runner de CI (bare, sem `.env`, sem os `environment:`/volumes do `docker-compose.yml`, usuário não-root). Ou seja: **nenhum alvo local reproduz o que `ci.yml` realmente faz** — os dois ambientes divergiram silenciosamente em exatamente os dois eixos que quebraram (um caminho de arquivo hardcoded assumindo container; uma dependência resolvida por hoisting do pnpm em vez de declarada). `make lint`/`make test` continuam corretos para o que se propõem (validar a aplicação como ela roda em container/produção) — a lacuna é a ausência de um jeito de validar o *workflow do CI em si* antes de dar push.

## Decisão

**Duas partes:**

### A. Corrigir as duas causas raiz (não são específicas do CI — são bugs reais de portabilidade)

1. `main.py` e `media/factory.py`: o fallback (quando `MEDIA_STORAGE_LOCAL_DIR` não está setado) passa a ser `tempfile.gettempdir() / "revold-media"` em vez de `/app/media` hardcoded — gravável em qualquer ambiente (container, CI, máquina local), sem depender de `WORKDIR`/root. Docker/produção continuam setando `MEDIA_STORAGE_LOCAL_DIR=/app/media` explicitamente via `docker-compose.yml` — comportamento inalterado nesses ambientes.
2. `packages/ui`: ganhou `.eslintrc.json` próprio (`@typescript-eslint/parser` + `plugin:@typescript-eslint/recommended`), `eslint`/`@typescript-eslint/*` como `devDependencies` explícitas (em vez de depender de hoisting de outro workspace) e `--ext .ts,.tsx` no script `lint`. Isso encontrou um `any` pré-existente em `sectionRegistry.ts` (registro de seções heterogêneo, tipo comum entre elas não existe além de `any`) — resolvido com um `eslint-disable-next-line` pontual e comentado, não um `any` silencioso nem a regra desligada globalmente.

### B. Adotar `act` para rodar `.github/workflows/ci.yml` localmente, com Docker (que já é pré-requisito único do projeto, ADR-0009)

`act` (nektos/act) executa o **mesmo arquivo YAML** que o GitHub Actions usa, em containers Docker que emulam a imagem do runner (`ubuntu-latest`) — sem passar pelo `docker-compose.yml`/Dockerfiles da aplicação, então nenhuma suposição "isso sempre roda dentro do meu container" sobrevive. É a única forma de reproduzir localmente exatamente a classe de bug que este ADR corrige, porque testar "dentro do container da aplicação" (o que `make test`/`make lint` já fazem bem) não é a mesma coisa que testar "nas condições do runner de CI".

- `.actrc` na raiz fixa uma imagem de runner leve (`catthehacker/ubuntu:act-latest`, ~500MB) em vez da imagem `-full` (dezenas de GB) que o `act` usaria por padrão.
- Novo alvo `make ci-local`: `act pull_request` (roda os dois jobs, `python` e `node`, exatamente como o `ci.yml` declara — incluindo o service container do Postgres).
- Documentado em `docs/guides/development.md`.

## Consequências

- As duas causas raiz corrigidas não voltam a quebrar silenciosamente: `make ci-local` (ou o próprio push) agora exercitaria as mesmas condições que expuseram os dois bugs.
- `act` precisa de Docker — já é o único pré-requisito do projeto (ADR-0009), então não é uma ferramenta nova para quem desenvolve, só um uso adicional do Docker que já precisa estar instalado. É preciso instalar o binário `act` em si (não vem com Docker).
- Fidelidade de `act` não é 100% idêntica ao runner hospedado da GitHub (a imagem `-latest` do `catthehacker` é uma aproximação, não a imagem oficial `ubuntu-latest` completa) — suficiente para pegar a classe de bug deste ADR (suposição de ambiente, dependência resolvida por acidente), não uma garantia absoluta de paridade com o runner real. `git push` para uma branch/PR continua sendo a validação final.
- Este ambiente de sandbox de nuvem roda como root, então `mkdir /app` "funcionava" por acidente aqui mesmo antes da correção — os testes deste ADR foram validados reproduzindo os comandos exatos do `ci.yml` (`poetry run pytest --collect-only`, depois a suíte completa; `pnpm -r lint`; `pnpm -r build`) e confirmando que o novo default (`tempfile.gettempdir()`) não depende de `/app` nem de privilégio de root — não foi possível rodar o próprio `act` neste ambiente (sem Docker funcional, mesma limitação já registrada na ADR-0020) nem no dispositivo do Samuel a partir desta sessão (sem Docker/poetry/pnpm/act instalados no shell usado só para operações de git) — validação final de `make ci-local` fica para a próxima vez que o Samuel rodar localmente.
- Suíte Python: `381 passed, 14 skipped` (mesmo baseline de antes), `ruff`/`mypy` limpos. `pnpm -r lint` e `pnpm -r build`: limpos nos 3 workspaces (`storefront`, `admin-dashboard`, `packages/ui`).
