# `storefront`

Loja virtual (Next.js 14, App Router). Site que roda sozinho: fala com o `api-gateway` por HTTP
e usa os componentes de `libs/web/ui`.

- **Tipo:** app · **Runtime:** next-web · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `ui`

## O que faz

Páginas de vitrine, coleções, busca, produto e lista de desejos, com a gaveta do carrinho, o
checkout por clique-para-conversar (ADR-0005) e o widget de chat do assistente. A vitrine é
composta por seções declaradas em `content/pages/` e renderizadas pelo `PageRenderer` de
`libs/web/ui` (ADR-0007).

## O que NÃO faz

- **Não importa pacote Python.** O que precisa da loja vem pela API; o contrato está em
  `products/ecommerce/contracts/api/`.
- **Não guarda componente reutilizável.** Componente sem regra da loja mora em `libs/web/ui`;
  aqui ficam os containers, que ligam o componente ao estado e à API.

## Rodar

```powershell
pnpm install                       # na raiz do monorepo
pnpm --filter storefront dev       # http://localhost:3000, precisa do api-gateway de pé
pnpm --filter storefront lint
pnpm --filter storefront build
```

Os testes são E2E, em Playwright, contra a pilha de verdade (ADR-0020): `make test-e2e`.
