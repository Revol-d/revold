# ADR-0010: Sessão de autenticação via cookie HttpOnly + Redis

**Status:** Aceito

## Contexto
`core-identity` (ADR-0003) já resolve *quem autentica* (provedores federados, sem senha própria) e já modela papéis (`Role.CUSTOMER/STAFF/ADMIN`). Faltava decidir *como o api-gateway lembra, entre uma requisição HTTP e outra, que um usuário está autenticado e quais papéis tem* — necessário agora porque os endpoints administrativos de estoque (`POST /api/inventory/{sku}/receive`, `/reserve`, `/release`) precisam de RBAC real (só STAFF/ADMIN), não só um comentário dizendo que isso viria depois.

Duas opções foram avaliadas:
1. **JWT (Bearer token, stateless)**: o backend assina um token após o login, contendo `user_id` + `roles`; o cliente manda em `Authorization: Bearer`. Sem estado no servidor.
2. **Sessão via cookie HttpOnly + Redis**: login gera uma sessão opaca guardada no Redis; o cookie carrega só o id da sessão, nenhum dado de usuário.

## Decisão
Usar sessão via cookie HttpOnly + Redis (opção 2).

Motivos:
- **Revogação instantânea.** Papel STAFF/ADMIN é sensível — precisa ser possível derrubar o acesso de alguém imediatamente (`DEL session:{id}` no Redis). Com JWT isso exigiria esperar o token expirar ou manter uma blocklist — reimplementando, com mais complexidade, o que uma sessão já dá de graça.
- **Redis já é infraestrutura existente** (usado por `core-cart`, ver `adapters_persistence.redis_client`) — não adiciona peça nova ao stack.
- **Superfície de XSS menor.** Cookie `HttpOnly` não é lido por JavaScript; um JWT guardado em `localStorage` (o lugar mais comum de guardar um Bearer token numa SPA) é.
- A vantagem clássica de JWT — evitar round-trip de validação em arquitetura distribuída/multisserviço — não se aplica aqui: o storefront e o admin falam com um único `api-gateway`, não com vários serviços independentes validando token cada um.

Design:
- `core_identity.ports.SessionRepository`: porta com `create(user) -> session_id`, `get(session_id) -> AuthenticatedUser | None`, `delete(session_id)`. Implementação Redis (`adapters_persistence.identity.RedisSessionRepository`) serializa `AuthenticatedUser` como JSON sob a chave `session:{id}`, com TTL de 7 dias (mesma janela usada pelo carrinho).
- `session_id` é gerado com `secrets.token_urlsafe(32)` (aleatoriedade criptográfica, não previsível).
- O cookie (`session_id`) é `HttpOnly`, `SameSite=Lax` e `Secure` em produção (`SESSION_COOKIE_SECURE`, configurável para `false` só em dev local sobre HTTP).
- `api_gateway.security` expõe `get_current_user` (401 se não autenticado) e `require_any_role(*roles)` (403 se autenticado mas sem o papel) — dependências FastAPI usadas pelos routers administrativos. Este módulo vive no api-gateway, não em `core_identity`, porque conhece FastAPI/`HTTPException` (um core não depende de framework web, ADR-0002).

## Consequências
- Login e RBAC exigem que o cliente (storefront/admin-dashboard) sempre mande cookies (`credentials: "include"` em `fetch`) — CORS já precisa de `allow_credentials=True` (já configurado em `main.py`).
- Fica fora do escopo desta ADR (e ainda não implementado): CSRF em requisições que mudam estado a partir de outro site. Como o cookie é `SameSite=Lax`, requisições cross-site simples (GET) são protegidas; POST/DELETE cross-site via formulário ainda dependem de `SameSite` — se o storefront algum dia precisar aceitar requisições de terceiros autenticadas, isso precisa de um token CSRF dedicado.
- Sem app mobile nativo nem terceiros consumindo a API hoje — se isso mudar no futuro, a porta `SessionRepository`/cookie deste ADR não serve para esses clientes, e um mecanismo complementar (ex.: JWT para API pública) precisaria ser adicionado ao lado, não em substituição.
- Continua usando `DevIdentityProvider` (ADR-0003) para gerar o `AuthenticatedUser` em desenvolvimento — este ADR não muda quem autentica, só como o resultado da autenticação é lembrado entre requisições.
