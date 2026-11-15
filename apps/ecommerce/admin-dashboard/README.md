# `admin-dashboard`

Painel administrativo da loja (Next.js 14, App Router). Site que roda sozinho: fala com o
`api-gateway` por HTTP.

- **Tipo:** app · **Runtime:** next-web · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

As telas de quem opera a loja: produtos (criar e editar, com as variantes), estoque, pedidos e
configurações da loja, além do login. As telas de operação pedem sessão com papel `STAFF` ou
`ADMIN`, e a de configurações, `ADMIN` (ADR-0010).

## O que NÃO faz

- **Não importa pacote Python.** O que precisa da loja vem pela API; o contrato está em
  `products/ecommerce/contracts/api/`.
- **Não decide permissão.** Quem autoriza é o `api-gateway`; a tela só reage a 401 e 403.

## Rodar

```powershell
pnpm install                            # na raiz do monorepo
pnpm --filter admin-dashboard dev       # http://localhost:3001, precisa do api-gateway de pé
pnpm --filter admin-dashboard lint
pnpm --filter admin-dashboard build
```

Ainda não há teste automatizado deste site. Está registrado em "Pontos em aberto" do
[CONTRIBUTING.md](../../../CONTRIBUTING.md).
