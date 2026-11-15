# ADR-0016: API key + rate limiter + webhook de saída (exposição de API pública/parceiro)

**Status:** Aceito

## Contexto

O `api-gateway`, até aqui, só atendia `storefront`/`admin-dashboard` internos, autenticados por sessão (cookie HttpOnly + Redis, ADR-0010) — sempre um navegador, sempre um humano logado. Não existia nenhuma porta para um chamador **externo** (um ERP, um segundo canal de venda, uma integração de parceiro): nem forma de autenticar sem sessão de navegador, nem proteção contra abuso de uso, nem forma de avisar um sistema externo quando algo acontece no domínio.

Isso é um leaf genérico e reutilizável do framework: qualquer projeto futuro que precise expor API para parceiro precisa dos mesmos três pedaços — autenticação por chave, limite de uso por chave, e entrega de evento pra fora. Nenhum dos três depende de credencial de nuvem nenhuma (Categoria A do `planejamento-leafs-e-adaptadores.md`): API key é dado nosso, guardado no nosso Postgres; rate limit usa o Redis que já está no compose; webhook é só uma chamada HTTP de saída.

## Decisão

**Duas portas novas em `core-identity`** (não um core novo — API key é só outra forma de identificar quem está chamando, mesmo bounded context de `AuthenticatedUser`/RBAC/sessão):

```python
class ApiKeyAuth(Protocol):
    async def issue(self, *, name: str) -> tuple[ApiKeyPrincipal, str]: ...
    async def resolve(self, raw_key: str) -> ApiKeyPrincipal | None: ...
    async def revoke(self, key_id: str) -> None: ...  # ApiKeyNotFound se não existir

class RateLimiter(Protocol):
    async def allow(self, principal_id: str, *, limit: int, window_seconds: int) -> bool: ...
```

- **`PostgresApiKeyAuth`** (`adapters/persistence`): a chave em texto puro (`rvld_<token urlsafe>`) só existe no retorno de `issue` — o que é persistido é só o hash sha256 dela (tabela `identity_api_keys`, migração 0005). `resolve` ignora chave revogada (`revoked_at` não nulo). Mesmo padrão de qualquer provedor real (GitHub, Stripe): perder a chave em texto puro depois de emitida é o esperado, não um bug.
- **`RedisRateLimiter`** (`adapters/persistence`): contador de janela fixa (`INCR`+`EXPIRE`, chave `ratelimit:{principal_id}:{window_seconds}`) — mais simples de implementar corretamente que um token bucket "de verdade", suficiente para proteger contra abuso. Cada chamador (`principal_id` = `key_id`) tem seu próprio contador.
- **`require_api_key_principal`** (`api_gateway.security`): lê o header `X-API-Key`, resolve via `ApiKeyAuth` (401 se ausente/inválida), aplica o rate limit via `RateLimiter` (429 se excedido — limite configurável via `PUBLIC_API_RATE_LIMIT`/`PUBLIC_API_RATE_LIMIT_WINDOW_SECONDS`, default 60 req/60s). Nunca se mistura com `get_current_user`/RBAC de sessão — são dois mecanismos de autenticação paralelos e independentes.
- **Endpoints novos**:
  - `POST/DELETE /api/auth/api-keys` — emitir/revogar chave, RBAC **ADMIN only** (mais restrito que os endpoints administrativos de catálogo/estoque, que também aceitam STAFF: dar acesso de API externa é mais sensível que editar produto).
  - `GET /api/public/v1/products` — primeiro endpoint da API pública/parceiro, protegido por `X-API-Key` + rate limit, prova de conceito do leaf inteiro. Mais endpoints entram aqui conforme surgir necessidade real de um parceiro.

**Porta nova em `core-events`** (complementa `EventPublisher`, não o substitui — production intern vs. entrega para fora):

```python
class WebhookSender(Protocol):
    async def send(self, url: str, event: DomainEvent) -> bool: ...
```

- **`LoggingWebhookSender`** (`adapters/messaging`, dev/default): só loga, sem chamada de rede.
- **`HttpWebhookSender`** (`adapters/messaging`, real): entrega HTTP com retry/backoff exponencial (3 tentativas por padrão). Testado de ponta a ponta contra um app FastAPI de teste via `httpx.ASGITransport` — zero servidor real precisando escutar numa porta, e ainda assim exercita o código de produção de verdade (não um mock da chamada HTTP).
- **`event_worker.dispatch.forward_to_webhooks`**: depois do processamento interno de qualquer evento (reindexação, notificação), encaminha o mesmo evento para cada URL em `WEBHOOK_URLS` (env var, vazia por padrão — nenhum parceiro configurado ainda). Falha de entrega em um destino não afeta os demais nem o processamento interno, que já aconteceu antes — best-effort de propósito.

## Testes

- `cores/core-identity/tests`: `IssueApiKey`/`RevokeApiKey` com `FakeApiKeyAuth` em memória.
- `adapters/persistence/tests/test_api_key_auth_integration.py` (`@pytest.mark.integration`): `PostgresApiKeyAuth` contra Postgres real — confirma que o texto puro nunca é persistido, resolve/revoke/erro de key_id inexistente.
- `adapters/persistence/tests/test_redis_rate_limiter.py`: `RedisRateLimiter` contra `fakeredis` (mesmo padrão de `test_redis_session_repository.py`) — limite respeitado, contadores independentes por principal, janela expira.
- `adapters/messaging/tests/test_logging_webhook_sender.py` e `test_http_webhook_sender.py`: sucesso na primeira tentativa, retry-até-dar-certo, esgotamento de tentativas — via ASGITransport.
- `workers/event-worker/tests/test_dispatch.py` e `test_celery_app_routing.py`: `forward_to_webhooks` isolado (fake sender) e o roteamento em `_dispatch` (webhook só é chamado quando `WEBHOOK_URLS` está configurada).
- `apps/api-gateway/tests/test_identity_routes.py`: emitir/revogar chave — RBAC ADMIN only (STAFF e sem-auth retornam 403/401).
- `apps/api-gateway/tests/test_public_api_routes.py`: sem header → 401, chave inválida → 401, chave válida → 200, rate limit excedido → 429, confirma que o rate limiter é chamado com o `key_id` correto.

## Consequências

- Nenhuma credencial nova é necessária — Postgres e Redis já são serviços do `docker-compose.yml`. O leaf inteiro (issue/resolve/revoke, rate limit, webhook com retry) está pronto para uso real hoje, sem esperar nenhuma conta externa.
- `WEBHOOK_URLS` vazio (default) é totalmente inerte — nenhuma chamada de rede acontece até um parceiro real ser configurado.
- Base pronta para qualquer projeto futuro do framework que precise expor API para parceiro/integração, sem inventar o mecanismo de novo.
