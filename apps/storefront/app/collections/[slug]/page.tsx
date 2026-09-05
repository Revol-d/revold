import { Breadcrumb, CategoryHeader, ProductCard } from "@revold/ui";
import { listProducts } from "@/lib/api";

export const dynamic = "force-dynamic";

interface CollectionPageProps {
  params: { slug: string };
  searchParams: { page?: string };
}

export default async function CollectionPage({ params, searchParams }: CollectionPageProps) {
  const page = Number(searchParams.page ?? "1");
  const result = await listProducts({ category: params.slug, page, pageSize: 24 });

  return (
    <main id="main-content">
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Coleções", href: "/collections" },
          { label: params.slug },
        ]}
      />
      <CategoryHeader title={params.slug} resultCount={result.total} />
      <div
        className="product-grid"
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "1.5rem" }}
      >
        {result.items.map((product) => (
          <ProductCard
            key={product.sku}
            sku={product.sku}
            name={product.name}
            imageUrl={product.images[0] ?? ""}
            imageAlt={product.name}
            price={product.price.amount}
            originalPrice={product.original_price?.amount}
            currency={product.price.currency}
            href={`/products/${product.sku}`}
          />
        ))}
      </div>
    </main>
  );
}
