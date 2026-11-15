"use client";
import { InlineCrossSell } from "@revold/ui";
import type { Product } from "@/lib/api";
import { useCart } from "@/lib/useCart";
import { useUIStore } from "@/store/uiStore";

export function CrossSellContainer({ title, products }: { title: string; products: Product[] }) {
  const { addItem } = useCart();
  const openCart = useUIStore((state) => state.openCart);

  if (products.length === 0) return null;

  return (
    <InlineCrossSell
      title={title}
      items={products.map((product) => ({
        sku: product.sku,
        name: product.name,
        imageUrl: product.images[0] ?? "",
        priceLabel: new Intl.NumberFormat("pt-BR", {
          style: "currency",
          currency: product.price.currency,
        }).format(Number(product.price.amount)),
        href: `/products/${product.sku}`,
      }))}
      onAdd={async (sku) => {
        const product = products.find((p) => p.sku === sku);
        if (!product) return;
        // Cross-sell adiciona a variante em estoque mais simples (primeira
        // disponível) — não há seletor de tamanho/cor nesta vitrine
        // compacta, por isso não faz sentido para um produto sem nenhuma
        // variante em estoque (o botão nem chega a aparecer nesse caso,
        // ver filtro em ProductDetailPage).
        const variant = product.variants.find((v) => v.in_stock);
        await addItem({
          sku: variant?.sku ?? product.sku,
          name: product.name,
          variant_label: variant ? `${variant.size} / ${variant.color}` : "Padrão",
          unit_price: product.price.amount,
        });
        openCart();
      }}
    />
  );
}
