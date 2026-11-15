"use client";
import { useEffect, useRef } from "react";

export interface CartLineItem {
  sku: string;
  name: string;
  variantLabel: string;
  quantity: number;
  unitPriceLabel: string;
  subtotalLabel: string;
  availableQuantity?: number | null;
}

export interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  items: CartLineItem[];
  totalLabel: string;
  onUpdateQuantity: (sku: string, quantity: number) => void;
  onRemove: (sku: string) => void;
  onCheckout: () => void;
  isCheckingOut?: boolean;
  checkoutError?: string;
  emptyMessage?: string;
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Mini-carrinho em drawer lateral. Foco preso dentro enquanto aberto, Esc
 * fecha, e o foco volta ao elemento que abriu o drawer ao fechar — sem isso
 * o foco "vaza" para trás do drawer (ver referencia-frontend-storefront.md,
 * seção 1). libs/web/ui não sabe formatar dinheiro nem chamar a API do
 * carrinho — os textos já vêm formatados e as ações já vêm como callbacks. */
export function CartDrawer({
  isOpen,
  onClose,
  items,
  totalLabel,
  onUpdateQuantity,
  onRemove,
  onCheckout,
  isCheckingOut = false,
  checkoutError,
  emptyMessage = "Seu carrinho está vazio.",
}: CartDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const focusable = panel?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    focusable?.[0]?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused.current?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="cart-drawer__overlay" onClick={onClose}>
      <div
        ref={panelRef}
        className="cart-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Carrinho de compras"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="cart-drawer__header">
          <h2>Seu carrinho</h2>
          <button type="button" onClick={onClose} aria-label="Fechar carrinho">
            <span aria-hidden="true">✕</span>
          </button>
        </div>

        {items.length === 0 ? (
          <p className="cart-drawer__empty">{emptyMessage}</p>
        ) : (
          <ul className="cart-drawer__items">
            {items.map((item) => (
              <li key={item.sku} className="cart-drawer__item">
                <div className="cart-drawer__item-info">
                  <p className="cart-drawer__item-name">{item.name}</p>
                  <p className="cart-drawer__item-variant">{item.variantLabel}</p>
                  <p className="cart-drawer__item-price">{item.unitPriceLabel}</p>
                  {typeof item.availableQuantity === "number" && item.availableQuantity < item.quantity && (
                    <p className="cart-drawer__item-warning" role="status">
                      Só {item.availableQuantity} em estoque
                    </p>
                  )}
                </div>
                <div className="cart-drawer__item-controls">
                  <label className="sr-only" htmlFor={`qty-${item.sku}`}>
                    Quantidade de {item.name}
                  </label>
                  <input
                    id={`qty-${item.sku}`}
                    type="number"
                    min={1}
                    value={item.quantity}
                    onChange={(e) => onUpdateQuantity(item.sku, Math.max(1, Number(e.target.value)))}
                  />
                  <button type="button" onClick={() => onRemove(item.sku)}>
                    Remover
                  </button>
                </div>
                <p className="cart-drawer__item-subtotal">{item.subtotalLabel}</p>
              </li>
            ))}
          </ul>
        )}

        <div className="cart-drawer__footer">
          <p className="cart-drawer__total" aria-live="polite">
            Total: {totalLabel}
          </p>
          {checkoutError && (
            <p className="cart-drawer__error" role="alert">
              {checkoutError}
            </p>
          )}
          <button
            type="button"
            className="cart-drawer__checkout"
            onClick={onCheckout}
            disabled={items.length === 0 || isCheckingOut}
          >
            {isCheckingOut ? "Abrindo WhatsApp…" : "Fechar pedido pelo WhatsApp"}
          </button>
        </div>
      </div>
    </div>
  );
}
