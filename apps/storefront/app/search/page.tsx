import { Breadcrumb, CategoryHeader } from "@revold/ui";
import { listProducts } from "@/lib/api";
import { ProductGrid } from "@/components/ProductGrid";

export const dynamic = "force-dynamic";

interface SearchPageProps {
  searchParams: { q?: string };
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const query = searchParams.q?.trim() ?? "";
  const result = query
    ? await listProducts({ q: query, pageSize: 48 })
    : { items: [], page: 1, page_size: 48, total: 0 };

  return (
    <main id="main-content">
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Busca" }]} />
      <CategoryHeader
        title={query ? `Resultados para "${query}"` : "Busca"}
        description={query ? undefined : "Digite algo na busca do topo da página."}
        resultCount={result.total}
      />
      <ProductGrid products={result.items} />
    </main>
  );
}
