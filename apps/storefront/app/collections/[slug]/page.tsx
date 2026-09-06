import { Breadcrumb, CategoryHeader } from "@revold/ui";
import type { SortValue } from "@revold/ui";
import { listCategories, listProducts } from "@/lib/api";
import { CollectionResults } from "@/components/CollectionResults";

export const dynamic = "force-dynamic";

interface CollectionPageProps {
  params: { slug: string };
  searchParams: { page?: string; sort?: string; q?: string; size?: string; color?: string };
}

const VALID_SORTS: SortValue[] = ["relevance", "price_asc", "price_desc"];

// "all" é um slug reservado do frontend (usado pelo CTA "Ver tudo" da home,
// ver content/pages/home.ts) — não existe categoria de verdade com esse
// slug, então aqui ele significa "sem filtro de categoria" em vez de ser
// repassado ao backend (que devolveria zero resultados).
const ALL_PRODUCTS_SLUG = "all";

// size/color chegam na URL como lista separada por vírgula (?size=P,M) —
// mantém o link compartilhável simples com múltiplos valores selecionados.
function parseCsv(value: string | undefined): string[] {
  return value ? value.split(",").filter(Boolean) : [];
}

export default async function CollectionPage({ params, searchParams }: CollectionPageProps) {
  const page = Number(searchParams.page ?? "1");
  const sort: SortValue = VALID_SORTS.includes(searchParams.sort as SortValue)
    ? (searchParams.sort as SortValue)
    : "relevance";
  const isAll = params.slug === ALL_PRODUCTS_SLUG;
  const category = isAll ? undefined : params.slug;
  const sizes = parseCsv(searchParams.size);
  const colors = parseCsv(searchParams.color);

  // Duas chamadas ao mesmo endpoint: uma filtrada (o que aparece na grade)
  // e uma sem size/color (só pra descobrir quais tamanhos/cores existem
  // nesta categoria+busca, e assim montar as opções do FilterPanel — se
  // usássemos a lista já filtrada, ao marcar "P" as opções de cor que só
  // existem em variantes "M" desapareceriam do painel).
  const [result, facetSource, categories] = await Promise.all([
    listProducts({ category, sort, q: searchParams.q, sizes, colors, page, pageSize: 24 }),
    listProducts({ category, q: searchParams.q, pageSize: 100 }),
    listCategories(),
  ]);

  const categoryName = isAll
    ? "Todos os produtos"
    : categories.find((c) => c.slug === params.slug)?.name ?? params.slug;

  return (
    <main id="main-content">
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Coleções", href: "/collections" },
          { label: categoryName },
        ]}
      />
      <CategoryHeader title={categoryName} resultCount={result.total} />
      <CollectionResults
        products={result.items}
        facetProducts={facetSource.items}
        sort={sort}
        sizes={sizes}
        colors={colors}
      />
    </main>
  );
}
