# `@revold/ui`

Componentes de interface e o renderizador de página por composição, usados pelos sites.

- **Tipo:** web · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

- `src/components/`: os componentes de apresentação (cartão de produto, galeria, filtros, gaveta
  do carrinho, widget de chat). Recebem dado e callbacks por propriedade.
- `src/composition/`: `PageRenderer`, o registro de seções e os tipos. Uma página é uma lista de
  seções declarada pelo site (ADR-0007).
- `src/tokens.css`: os tokens visuais.

## O que NÃO faz

- **Não faz fetch nem conhece a API.** Quem busca dado é o site.
- **Não conhece a marca nem a loja.** Logo, itens de navegação e textos chegam por propriedade.
- **Não formata dinheiro nem decide regra.** Isso é do site ou da API.

## Rodar

```powershell
pnpm install                    # na raiz do monorepo
pnpm --filter @revold/ui lint
```

O script `test` chama o Vitest, mas ainda não há arquivo de teste nesta lib. Está registrado em
"Pontos em aberto" do [CONTRIBUTING.md](../../../CONTRIBUTING.md).
