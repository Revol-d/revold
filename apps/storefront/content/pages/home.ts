import type { PageComposition } from "@revold/ui";

/** Composição da home. Mudar o layout da home é editar esta lista — trocar a
 * ordem das seções, remover o HeroBanner, mudar o limite do ProductGrid —
 * sem tocar em nenhum componente (ver ADR-0007). Uma seção verdadeiramente
 * nova ainda exige escrever o componente em packages/ui, mas recompor o que
 * já existe é só isto. */
export const homeComposition: PageComposition = [
  {
    type: "HeroBanner",
    props: {
      title: "Nova coleção",
      subtitle: "Peças pensadas para o seu dia a dia",
      imageUrl: "https://images.unsplash.com/photo-1441984904996-e0b6ba687e04?w=1600",
      imageAlt: "Roupas em exposição em uma arara de loja",
      ctaLabel: "Ver tudo",
      ctaHref: "/collections/all",
    },
  },
  {
    type: "ProductGrid",
    props: {
      title: "Mais vendidos",
      limit: 8,
    },
  },
];
