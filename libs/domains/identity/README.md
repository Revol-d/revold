# `revold_identity`

Identidade: login federado, sessão, papéis, API key e limite de requisições.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `azure-sql`

## O que faz

Os casos de uso de login, sessão e API key (ADR-0003, ADR-0010, ADR-0016), as portas `IdentityProvider`, `SessionRepository`, `ApiKeyAuth` e `RateLimiter`, e os adapters: `adapters/providers/` (dev e a factory `build_identity_provider`), `adapters/redis/` (sessão e limite por janela fixa) e `adapters/azure_sql/` (API key guardada como hash).

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não conhece FastAPI nem cookie.** A tradução de cookie e cabeçalho é do app (`api_gateway.security`).
- **Não guarda senha.** A autenticação é federada (ADR-0003).

## Testes

```powershell
uv run pytest libs/domains/identity/tests -q
```
