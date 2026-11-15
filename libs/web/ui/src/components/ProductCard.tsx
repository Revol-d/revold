import { PriceTag } from "./PriceTag";
import { DiscountBadge } from "./DiscountBadge";
import { RatingStars } from "./RatingStars";
import { WishlistToggle } from "./WishlistToggle";

export interface ProductCardProps {
  sku: string;
  name: string;
  imageUrl: string;
  imageAlt: string;
  price: string;
  originalPrice?: string;
  currency?: string;
  href: string;
  rating?: { value: number; count: number };
  isWishlisted?: boolean;
  onToggleWishlist?: (sku: string) => void;
}

function percentOff(price: string, originalPrice?: string): number {
  if (!originalPrice) return 0;
  const current = Number(price);
  const original = Number(originalPrice);
  if (!original || original <= current) return 0;
  return Math.round((1 - current / original) * 100);
}

export function ProductCard({
  sku,
  name,
  imageUrl,
  imageAlt,
  price,
  originalPrice,
  currency,
  href,
  rating,
  isWishlisted = false,
  onToggleWishlist,
}: ProductCardProps) {
  const discount = percentOff(price, originalPrice);
  return (
    <article className="product-card">
      <div className="product-card__media">
        {/* Em apps/ecommerce/storefront isto é substituído por next/image; libs/web/ui
            fica agnóstico de framework de imagem. */}
        <img src={imageUrl} alt={imageAlt} loading="lazy" />
        {discount > 0 && <DiscountBadge percentOff={discount} />}
        {onToggleWishlist && (
          <WishlistToggle
            productName={name}
            isActive={isWishlisted}
            onToggle={() => onToggleWishlist(sku)}
            className="product-card__wishlist"
          />
        )}
      </div>
      <a href={href} className="product-card__body">
        <h3 className="product-card__name">{name}</h3>
        <PriceTag amount={price} originalAmount={originalPrice} currency={currency} />
        {rating && <RatingStars value={rating.value} count={rating.count} />}
      </a>
    </article>
  );
}
