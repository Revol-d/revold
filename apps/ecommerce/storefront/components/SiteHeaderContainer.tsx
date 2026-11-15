"use client";
import { useRouter, usePathname } from "next/navigation";
import { SiteHeader, type NavMenuItem } from "@revold/ui";
import { useCart } from "@/lib/useCart";
import { useUIStore } from "@/store/uiStore";
import { useWishlist } from "@/lib/wishlist";

export interface SiteHeaderContainerProps {
  navItems: NavMenuItem[];
}

export function SiteHeaderContainer({ navItems }: SiteHeaderContainerProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { itemCount } = useCart();
  const openCart = useUIStore((state) => state.openCart);
  const { skus } = useWishlist();

  return (
    <SiteHeader
      logo={<span className="site-header__logo-text">Nick</span>}
      logoHref="/"
      navItems={navItems}
      currentHref={pathname}
      onSearchSubmit={(query) => {
        if (query) router.push(`/search?q=${encodeURIComponent(query)}`);
      }}
      wishlistHref="/wishlist"
      wishlistCount={skus.length}
      cartCount={itemCount}
      onCartOpen={openCart}
    />
  );
}
