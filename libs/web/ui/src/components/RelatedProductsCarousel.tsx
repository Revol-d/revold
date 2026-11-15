"use client";
import { useRef } from "react";
import { ProductCard, type ProductCardProps } from "./ProductCard";

export interface RelatedProductsCarouselProps {
  title: string;
  products: ProductCardProps[];
}

/** Carrossel de relacionados — os botões de anterior/próximo ficam sempre
 * visíveis (não só no hover) e o carrossel é operável por teclado: cada
 * ProductCard é um link focável na ordem natural do DOM, e os botões apenas
 * rolam o contêiner (ver referencia-frontend-storefront.md, seção 1). */
export function RelatedProductsCarousel({ title, products }: RelatedProductsCarouselProps) {
  const trackRef = useRef<HTMLDivElement>(null);

  function scrollBy(delta: number) {
    trackRef.current?.scrollBy({ left: delta, behavior: "smooth" });
  }

  if (products.length === 0) return null;

  return (
    <section className="related-products-carousel">
      <div className="related-products-carousel__header">
        <h2>{title}</h2>
        <div className="related-products-carousel__controls">
          <button type="button" aria-label="Ver produtos anteriores" onClick={() => scrollBy(-320)}>
            <span aria-hidden="true">‹</span>
          </button>
          <button type="button" aria-label="Ver mais produtos" onClick={() => scrollBy(320)}>
            <span aria-hidden="true">›</span>
          </button>
        </div>
      </div>
      <div className="related-products-carousel__track" ref={trackRef}>
        {products.map((product) => (
          <div key={product.sku} className="related-products-carousel__item">
            <ProductCard {...product} />
          </div>
        ))}
      </div>
    </section>
  );
}
