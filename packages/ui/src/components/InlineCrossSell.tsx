"use client";
import { useState } from "react";

export interface CrossSellItem {
  sku: string;
  name: string;
  imageUrl: string;
  priceLabel: string;
  href: string;
}

export interface InlineCrossSellProps {
  title: string;
  items: CrossSellItem[];
  onAdd: (sku: string) => void | Promise<void>;
}

/** Cross-sell inline ("combine com") — adicionar sem sair da página, com
 * feedback de sucesso anunciado por `aria-live`, não só um toast visual (ver
 * referencia-frontend-storefront.md, seção 1). */
export function InlineCrossSell({ title, items, onAdd }: InlineCrossSellProps) {
  const [status, setStatus] = useState<string>("");
  const [addingSku, setAddingSku] = useState<string | null>(null);

  async function handleAdd(sku: string, name: string) {
    setAddingSku(sku);
    try {
      await onAdd(sku);
      setStatus(`${name} adicionado ao carrinho.`);
    } finally {
      setAddingSku(null);
    }
  }

  if (items.length === 0) return null;

  return (
    <section className="inline-cross-sell">
      <h2>{title}</h2>
      <ul className="inline-cross-sell__list">
        {items.map((item) => (
          <li key={item.sku} className="inline-cross-sell__item">
            <a href={item.href}>
              <img src={item.imageUrl} alt={item.name} loading="lazy" />
              <span>{item.name}</span>
            </a>
            <span className="inline-cross-sell__price">{item.priceLabel}</span>
            <button
              type="button"
              onClick={() => handleAdd(item.sku, item.name)}
              disabled={addingSku === item.sku}
            >
              {addingSku === item.sku ? "Adicionando…" : "Adicionar"}
            </button>
          </li>
        ))}
      </ul>
      <p aria-live="polite" className="sr-only">
        {status}
      </p>
    </section>
  );
}
