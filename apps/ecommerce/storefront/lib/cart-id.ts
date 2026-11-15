/** O carrinho é identificado por um cart_id opaco gerado pelo frontend (ver
 * products/ecommerce/contracts/api/cart.yaml) — sem exigir login. Guardado em localStorage:
 * sobrevive a recarregar a página, mas é por navegador (não sincroniza
 * entre dispositivos, o que está de acordo com o MVP sem carrinho ligado a
 * conta de usuário). Só roda no navegador — nunca é chamado durante SSR. */
const STORAGE_KEY = "revold_cart_id";

export function getOrCreateCartId(): string {
  if (typeof window === "undefined") {
    throw new Error("getOrCreateCartId só pode ser chamado no navegador");
  }
  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) return existing;
  const created = window.crypto.randomUUID();
  window.localStorage.setItem(STORAGE_KEY, created);
  return created;
}
