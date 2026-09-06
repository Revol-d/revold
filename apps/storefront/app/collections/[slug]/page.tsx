import { Breadcrumb, CategoryHeader } from "@revold/ui";
import type { SortValue } from "@revold/ui";
import { listCategories, listProducts } from "@/lib/api";
import { CollectionResults } from "@/components/CollectionResults";

export const dynamic = "force-dynamic";

interface CollectionPageProps {
  params: { slug: string };
  searchParams: { page?: string; sort?: string; q?: string };
}

const VALID_SORTS: SortValue[] = ["relevance", "price_asc", "price_desc"];

// "all" é um slug reservado do frontend (usado pelo CTA "Ver tudo" da home,
// ver content/pages/home.ts) — não existe categoria de verdade com esse
// slug, então aqui ele significa "sem filtro de categoria" em vez de ser
// repassado ao backend (que devolveria zero resultados).
const ALL_PRODUCTS_SLUG = "all";

export default async function CollectionPage({ params, searchParams }: CollectionPageProps) {
  const page = Number(searchParams.page ?? "1");
  const sort: SortValue = VALID_SORTS.includes(searchParams.sort as SortValue)
    ? (searchParams.sort as SortValue)
    : "relevance";
  const isAll = params.slug === ALL_PRODUCTS_SLUG;

  const [result, categories] = await Promise.all([
    listProducts({
      category: isAll ? undefined : params.slug,
      sort,
      q: searchParams.q,
      page,
      pageSize: 24,
    }),
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
      <CollectionResults products={result.items} sort={sort} />
    </main>
  );
}
