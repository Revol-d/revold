"use client";
import { useCallback, useEffect, useState } from "react";

/** Lista de desejos client-side (localStorage) — não existe porta de
 * wishlist no backend hoje (core-catalog/core-cart não modelam isso ainda),
 * então isto é deliberadamente local ao navegador. Se um dia a Nick quiser
 * wishlist ligada à conta do cliente, isso vira um novo caso de uso em
 * core-cart ou um core novo, e este hook passa a chamar a API em vez do
 * localStorage — a interface pro resto do app (toggle/has) não muda. */
const STORAGE_KEY = "revold_wishlist";

function readStoredSkus(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export function useWishlist() {
  const [skus, setSkus] = useState<string[]>([]);

  useEffect(() => {
    setSkus(readStoredSkus());
  }, []);

  const toggle = useCallback((sku: string) => {
    setSkus((current) => {
      const next = current.includes(sku) ? current.filter((s) => s !== sku) : [...current, sku];
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // localStorage indisponível (modo privado, etc.) — segue só em memória
      }
      return next;
    });
  }, []);

  const has = useCallback((sku: string) => skus.includes(sku), [skus]);

  return { skus, has, toggle };
}
