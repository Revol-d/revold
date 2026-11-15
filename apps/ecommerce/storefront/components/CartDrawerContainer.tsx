"use client";
import { CartDrawer, type CartLineItem } from "@revold/ui";
import { useCart } from "@/lib/useCart";
import { useUIStore } from "@/store/uiStore";

function formatMoney(amount: string, currency: string): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(Number(amount));
}

export function CartDrawerContainer() {
  const isCartOpen = useUIStore((state) => state.isCartOpen);
  const closeCart = useUIStore((state) => state.closeCart);
  const { cart, items, updateQuantity, removeItem, checkout, isCheckingOut, checkoutError } = useCart();
  const currency = cart?.currency ?? "BRL";

  const lineItems: CartLineItem[] = items.map((item) => ({
    sku: item.sku,
    name: item.name,
    variantLabel: item.variant_label,
    quantity: item.quantity,
    unitPriceLabel: formatMoney(item.unit_price, currency),
    subtotalLabel: formatMoney(String(Number(item.unit_price) * item.quantity), currency),
    availableQuantity: item.available_quantity,
  }));

  async function handleCheckout() {
    const result = await checkout();
    window.open(result.handoff_url, "_blank", "noopener,noreferrer");
  }

  return (
    <CartDrawer
      isOpen={isCartOpen}
      onClose={closeCart}
      items={lineItems}
      totalLabel={formatMoney(cart?.total ?? "0", currency)}
      onUpdateQuantity={updateQuantity}
      onRemove={removeItem}
      onCheckout={handleCheckout}
      isCheckingOut={isCheckingOut}
      checkoutError={checkoutError}
    />
  );
}
