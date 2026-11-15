"use client";
import { ProductCard } from "@revold/ui";
import type { Product } from "@/lib/api";
import { useWishlist } from "@/lib/wishlist";

export function ProductGrid({ products, compact = false }: { products: Product[]; compact?: boolean }) {
  const { has, toggle } = useWishlist();

  return (
    <div
      className={`product-grid ${compact ? "product-grid--compact" : ""}`}
      style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "1.5rem" }}
    >
      {products.map((product) => (
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
          isWishlisted={has(product.sku)}
          onToggleWishlist={toggle}
        />
      ))}
    </div>
  );
}
