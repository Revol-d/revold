import { PageRenderer, ProductCard, productGridPropsSchema } from "@revold/ui";
import { homeComposition } from "@/content/pages/home";
import { listProducts } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  return (
    <main id="main-content">
      <PageRenderer
        sections={homeComposition}
        renderDynamicSection={(section, index) => {
          if (section.type !== "ProductGrid") return undefined;
          return <ProductGridSection key={index} {...productGridPropsSchema.parse(section.props)} />;
        }}
      />
    </main>
  );
}

async function ProductGridSection({
  title,
  categorySlug,
  limit,
}: {
  title?: string;
  categorySlug?: string;
  limit: number;
}) {
  const page = await listProducts({ category: categorySlug, pageSize: limit });
  return (
    <section className="product-grid-section">
      {title && <h2>{title}</h2>}
      <div className="product-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "1.5rem" }}>
        {page.items.map((product) => (
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
    </section>
  );
}
