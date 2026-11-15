"use client";
import { useState } from "react";

export interface ProductGalleryProps {
  images: string[];
  productName: string;
}

export function ProductGallery({ images, productName }: ProductGalleryProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const safeImages = images.length > 0 ? images : [""];

  return (
    <div className="product-gallery">
      <div className="product-gallery__main">
        <img src={safeImages[activeIndex]} alt={`${productName} — foto ${activeIndex + 1} de ${safeImages.length}`} />
      </div>
      {safeImages.length > 1 && (
        <div className="product-gallery__thumbs" role="tablist" aria-label="Fotos do produto">
          {safeImages.map((src, index) => (
            <button
              key={src + index}
              type="button"
              role="tab"
              aria-selected={index === activeIndex}
              aria-label={`Ver foto ${index + 1} de ${safeImages.length}`}
              className="product-gallery__thumb"
              onClick={() => setActiveIndex(index)}
            >
              <img src={src} alt="" aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
