"use client";
import { useMemo, useState } from "react";
import { ColorSwatch, SizeSelector } from "@revold/ui";
import type { Product } from "@/lib/api";
import { AddToCartButton } from "@/components/AddToCartButton";

export function ProductVariantPicker({ product }: { product: Product }) {
  const sizes = useMemo(() => {
    const seen = new Map<string, boolean>();
    for (const variant of product.variants) {
      seen.set(variant.size, (seen.get(variant.size) ?? false) || variant.in_stock);
    }
    return [...seen.entries()].map(([value, available]) => ({ value, label: value, available }));
  }, [product.variants]);

  const colors = useMemo(() => {
    const seen = new Map<string, boolean>();
    for (const variant of product.variants) {
      seen.set(variant.color, (seen.get(variant.color) ?? false) || variant.in_stock);
    }
    return [...seen.entries()].map(([value, available]) => ({ value, label: value, available }));
  }, [product.variants]);

  const [selectedSize, setSelectedSize] = useState<string | undefined>(
    sizes.find((s) => s.available)?.value,
  );
  const [selectedColor, setSelectedColor] = useState<string | undefined>(
    colors.find((c) => c.available)?.value,
  );

  const selectedVariant = product.variants.find(
    (v) => v.size === selectedSize && v.color === selectedColor,
  );
  // Produto sem variante cadastrada (ex.: peça única, sem grade de
  // tamanho/cor) — não há o que selecionar, o próprio SKU do produto
  // representa a linha do carrinho.
  const hasNoVariants = product.variants.length === 0;
  const canAdd = hasNoVariants || Boolean(selectedVariant?.in_stock);

  return (
    <div className="product-variant-picker">
      {colors.length > 0 && (
        <div className="product-variant-picker__group">
          <ColorSwatch options={colors} selected={selectedColor} onSelect={setSelectedColor} />
        </div>
      )}
      {sizes.length > 0 && (
        <div className="product-variant-picker__group">
          <SizeSelector options={sizes} selected={selectedSize} onSelect={setSelectedSize} />
        </div>
      )}
      {selectedSize && selectedColor && !selectedVariant && (
        <p className="product-variant-picker__unavailable" role="status">
          Essa combinação de tamanho e cor não existe para este produto.
        </p>
      )}
      <AddToCartButton
        sku={selectedVariant?.sku ?? product.sku}
        name={product.name}
        variantLabel={selectedSize && selectedColor ? `${selectedSize} / ${selectedColor}` : "Padrão"}
        unitPrice={product.price.amount}
        disabled={!canAdd}
        disabledLabel={
          selectedSize && selectedColor && selectedVariant && !selectedVariant.in_stock
            ? "Esgotado"
            : "Selecione tamanho e cor"
        }
      />
    </div>
  );
}
