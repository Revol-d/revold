# ADR-0019: core-store-settings — configuração da loja editável pela Nick

**Status:** Aceito

## Contexto

O `Readme.md` lista, como requisito funcional explícito do MVP, uma tela editável pela Nick com "CNPJ, Informações de contato, Dados da loja, Configurações gerais". Essa tela nunca foi construída nem havia porta em nenhum core para esse dado — era uma lacuna genuína (documentada em `claude/status-implementacao.md` desde a primeira avaliação macro do projeto).

Esse dado não é catálogo (`core-catalog`), não é estoque (`core-inventory`) nem identidade de usuário (`core-identity`) — é dado administrativo da própria empresa/loja. Forçar esse dado dentro de um core existente misturaria um conceito estranho ao bounded context (ADR-0002 exige separação por conceito de domínio, não por "onde encaixa por enquanto").

Havia também uma configuração "geral" já existente, mas presa em variável de ambiente: `LOW_STOCK_THRESHOLD`, que definia o limiar de estoque baixo (ADR-0013, `NotifyLowStock`) e só podia ser mudada com um novo deploy — o oposto de "configuração editável pela Nick".

## Decisão

**Novo core pequeno, `core-store-settings`** — um único registro de configuração (não há múltiplas lojas hoje):

- **Domínio**: `StoreSettings` (dataclass congelado) com `cnpj`, `store_name`, `contact_email`, `contact_phone`, `store_address`, `low_stock_threshold`. Validação: CNPJ (se informado) precisa ter 14 dígitos (com ou sem máscara — só os dígitos são validados); e-mail (se informado) precisa ter `@`; limiar não pode ser negativo. Todo campo textual pode ficar vazio (loja ainda não configurada).
- **Porta**: `StoreSettingsRepository` (`get() -> StoreSettings | None`, `save(settings) -> None`) — `None` representa "a Nick ainda não configurou nada".
- **Casos de uso**: `GetStoreSettings` (com fallback para um registro vazio usando `LOW_STOCK_THRESHOLD` como limiar padrão quando nada foi salvo — preserva o comportamento anterior para quem nunca abrir a tela) e `UpdateStoreSettings` (atualização parcial — só os campos informados mudam, mesmo padrão de `UpdateProduct` em `core-catalog`).
- **Adapter**: `PostgresStoreSettingsRepository` (`adapters/persistence`) — tabela `store_settings` com um único registro de id fixo (`"default"`); `save()` faz upsert nele. Migração `0006_store_settings.py`.
- **API**: `GET/PUT /api/store-settings` — **RBAC ADMIN only** (mais restrito que catálogo/estoque, que também aceitam STAFF: CNPJ e contato são dado mais sensível). `PUT` aceita atualização parcial e devolve 422 se CNPJ/e-mail tiverem formato inválido.
- **`LOW_STOCK_THRESHOLD` migrado de env var fixa para configuração viva**: `api_gateway.dependencies.get_low_stock_threshold` (usado por `reserve_stock` em `core-inventory` e pelo fluxo de checkout em `core-cart`) agora lê `core-store-settings` a cada requisição, caindo na env var só quando a Nick nunca salvou nada. Editar o limiar em `/configuracoes` tem efeito imediato, sem deploy — a env var continua existindo só como piso/compatibilidade.
- **Frontend**: `apps/admin-dashboard/app/configuracoes/page.tsx` — formulário único (RBAC ADMIN, mesma checagem de papel das outras telas administrativas), link a partir da home do admin-dashboard.

## Testes

- `cores/core-store-settings/tests`: domínio (validação de CNPJ/e-mail/limiar) + casos de uso (fallback vazio, atualização parcial) contra um fake em memória.
- `adapters/persistence/tests/test_store_settings_repository_integration.py` (`@pytest.mark.integration`): contra Postgres real — `get()` antes de qualquer `save()`, round-trip completo, upsert (duas chamadas de `save()` não criam um segundo registro).
- `apps/api-gateway/tests/test_store_settings_routes.py`: RBAC (401 sem sessão, 403 STAFF, 200 ADMIN), atualização parcial, 422 em CNPJ inválido.
- `apps/api-gateway/tests/test_cart_routes.py`, `test_inventory_routes.py`, `test_inventory_rbac.py`: `get_low_stock_threshold` (agora dependente de Postgres) sobrescrito com o valor padrão de antes (5) nesses testes de unidade, para não abrir uma sessão de banco de verdade fora do fluxo que o teste quer exercitar (mesmo cuidado já documentado em `test_metrics_endpoint.py` sobre o event loop por teste do pytest-asyncio vs. o engine async singleton).

## Consequências

- Fecha o requisito funcional explícito do `Readme.md` que seguia sem nenhuma linha de código.
- `LOW_STOCK_THRESHOLD` deixa de exigir deploy para ser ajustado — primeira configuração "geral" do sistema a virar editável em tempo real pela Nick.
- Um único registro é suficiente hoje (uma loja só); se o monorepo vier a hospedar múltiplos tenants no futuro, `StoreSettingsRepository` precisaria ganhar uma chave de tenant — não é um redesenho grande (mesma forma de porta, só a chave de busca muda), mas não foi feito agora (YAGNI).
- CNPJ é guardado como o texto que a Nick digitar (com ou sem máscara) — só a validação normaliza para dígitos; não há checagem de dígito verificador (fora de escopo: o formulário está para configuração administrativa interna, não para validação de cadastro fiscal).
