"use client";
import { useEffect, useState } from "react";
import { Breadcrumb } from "@revold/ui";
import { getProduct, type Product } from "@/lib/api";
import { useWishlist } from "@/lib/wishlist";
import { ProductGrid } from "@/components/ProductGrid";

/** Página client-side pura: a wishlist em si é só localStorage (não existe
 * porta de wishlist no backend hoje — ver lib/wishlist.ts), então esta
 * página busca cada produto favoritado individualmente no catálogo (não há
 * endpoint de busca em lote) e ignora SKUs que não existem mais. */
export default function WishlistPage() {
  const { skus } = useWishlist();
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    Promise.all(skus.map((sku) => getProduct(sku).catch(() => null))).then((results) => {
      if (cancelled) return;
      setProducts(results.filter((p): p is Product => p !== null));
      setIsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [skus]);

  return (
    <main id="main-content">
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Lista de desejos" }]} />
      <h1>Lista de desejos</h1>
      {isLoading && <p>Carregando…</p>}
      {!isLoading && products.length === 0 && <p>Você ainda não adicionou nenhum produto à lista de desejos.</p>}
      {!isLoading && products.length > 0 && <ProductGrid products={products} />}
    </main>
  );
}
