"use client";
import { useState } from "react";
import { useCart } from "@/lib/useCart";
import { useUIStore } from "@/store/uiStore";

export interface AddToCartButtonProps {
  sku: string;
  name: string;
  variantLabel: string;
  unitPrice: string;
  disabled?: boolean;
  disabledLabel?: string;
}

/** Botão de adicionar ao carrinho da PDP — depois de adicionar, abre o
 * drawer (feedback claro de que a ação funcionou) e anuncia por
 * `aria-live`, não só a mudança visual do contador no header. */
export function AddToCartButton({
  sku,
  name,
  variantLabel,
  unitPrice,
  disabled,
  disabledLabel = "Selecione tamanho e cor",
}: AddToCartButtonProps) {
  const { addItem, isAdding } = useCart();
  const openCart = useUIStore((state) => state.openCart);
  const [status, setStatus] = useState("");

  async function handleClick() {
    await addItem({ sku, name, variant_label: variantLabel, unit_price: unitPrice });
    setStatus(`${name} (${variantLabel}) adicionado ao carrinho.`);
    openCart();
  }

  return (
    <>
      <button type="button" className="add-to-cart-button" onClick={handleClick} disabled={disabled || isAdding}>
        {isAdding ? "Adicionando…" : disabled ? disabledLabel : "Adicionar ao carrinho"}
      </button>
      <p aria-live="polite" className="sr-only">
        {status}
      </p>
    </>
  );
}
