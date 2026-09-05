# ADR-0007: Frontend orientado a composição (layout como dado, sem ferramenta de design)

**Status:** Aceito

## Contexto
Decisão explícita: não usar Figma/wireframing como etapa do processo. O requisito é que a UI seja boa o suficiente e bem desacoplada para que mudar o layout do site seja rápido — inclusive via prompt, alterando código/configuração diretamente — em vez de depender de uma ferramenta de design separada do código.

## Decisão
`packages/ui` fornece um conjunto de componentes primitivos e de seção (`ProductCard`, `CategoryHeader`, `HeroBanner`, `Accordion`, `CartDrawer` etc. — ver `referencia-frontend-storefront.md` no projeto Claude para o inventário completo), cada um com props tipadas e sem nenhuma referência a conteúdo específico da Nick.

`apps/storefront` (e qualquer app futuro) monta páginas através de um **`PageRenderer`**: um componente que recebe uma lista ordenada de seções — `{ type: "HeroBanner", props: {...} }`, `{ type: "ProductGrid", props: {...} }` etc. — e resolve cada `type` para o componente correspondente de `packages/ui` através de um registro (`sectionRegistry`). A composição de cada página vive como dado (arquivo `.ts`/`.json` em `apps/storefront/content/pages/`), não como JSX escrito à mão por página.

Consequência direta: mudar o layout de uma página é editar a lista de seções e suas props (uma tarefa que um prompt resolve com precisão, por ser uma edição estruturada, não uma reinterpretação visual) — não é preciso mexer nos componentes nem em uma ferramenta externa de design.

## Consequências
- Exige que `packages/ui` seja bem tipado desde o início (props de cada seção validadas, ex. com Zod) para que uma composição inválida falhe cedo (erro de tipo/validação), não silenciosamente em produção.
- Layouts muito fora do padrão (uma seção verdadeiramente única, usada uma vez só) ainda exigem escrever um componente novo — o `PageRenderer` acelera recomposição do que já existe, não substitui design de componente novo.
- Esse mesmo mecanismo é reutilizável em projetos futuros do monorepo: um novo projeto ganha o `PageRenderer` e o catálogo de seções prontos, só precisa das seções específicas do seu domínio.
