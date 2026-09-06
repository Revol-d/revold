import { PageRenderer, productGridPropsSchema } from "@revold/ui";
import { homeComposition } from "@/content/pages/home";
import { listProducts } from "@/lib/api";
import { ProductGrid } from "@/components/ProductGrid";

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
      <ProductGrid products={page.items} />
    </section>
  );
}
