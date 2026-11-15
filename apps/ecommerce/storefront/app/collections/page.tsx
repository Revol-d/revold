import { Breadcrumb } from "@revold/ui";
import { listCategories } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CollectionsIndexPage() {
  const categories = await listCategories();

  return (
    <main id="main-content">
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Coleções" }]} />
      <h1>Coleções</h1>
      <ul className="collections-index">
        {categories.map((category) => (
          <li key={category.slug}>
            <a href={`/collections/${category.slug}`}>{category.name}</a>
          </li>
        ))}
      </ul>
    </main>
  );
}
