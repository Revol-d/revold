/** Cliente HTTP tipado para o api-gateway (autenticação + catálogo +
 * estoque). Mesmo racional de apps/storefront/lib/api.ts: espelha os
 * contratos (contracts/api/identity.yaml, catalog.yaml, inventory.yaml)
 * manualmente por enquanto. Todas as chamadas usam `credentials: "include"`
 * para enviar/receber o cookie de sessão HttpOnly (ADR-0010). */

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:8000";

export interface AuthenticatedUser {
  external_id: string;
  provider: string;
  email: string;
  name: string;
  roles: string[];
}

export interface LoginChallenge {
  authorize_url: string;
  state: string;
}

export interface Money {
  amount: string;
  currency: string;
}

export interface Category {
  slug: string;
  name: string;
}

export interface ProductVariantInput {
  sku: string;
  size: string;
  color: string;
  in_stock: boolean;
}

export interface Product {
  sku: string;
  name: string;
  description: string;
  price: Money;
}

export interface ProductPage {
  items: Product[];
  page: number;
  page_size: number;
  total: number;
}

export interface StockLevel {
  sku: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Erro ${response.status} ao chamar ${path}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function startLogin(redirectUri: string): Promise<LoginChallenge> {
  return apiFetch<LoginChallenge>("/api/auth/login/start", {
    method: "POST",
    body: JSON.stringify({ redirect_uri: redirectUri }),
  });
}

export function completeLogin(code: string, state: string): Promise<AuthenticatedUser> {
  return apiFetch<AuthenticatedUser>("/api/auth/login/complete", {
    method: "POST",
    body: JSON.stringify({ code, state }),
  });
}

export function logout(): Promise<void> {
  return apiFetch<void>("/api/auth/logout", { method: "POST" });
}

export function getCurrentUser(): Promise<AuthenticatedUser> {
  return apiFetch<AuthenticatedUser>("/api/auth/me");
}

export function listProducts(page = 1, pageSize = 24): Promise<ProductPage> {
  return apiFetch<ProductPage>(`/api/catalog/products?page=${page}&page_size=${pageSize}`);
}

export function listCategories(): Promise<Category[]> {
  return apiFetch<Category[]>("/api/catalog/categories");
}

export function createCategory(slug: string, name: string): Promise<Category> {
  return apiFetch<Category>("/api/catalog/categories", {
    method: "POST",
    body: JSON.stringify({ slug, name }),
  });
}

export function createProduct(input: {
  sku: string;
  name: string;
  categorySlug: string;
  priceAmount: string;
  description?: string;
  variants: ProductVariantInput[];
}): Promise<Product> {
  return apiFetch<Product>("/api/catalog/products", {
    method: "POST",
    body: JSON.stringify({
      sku: input.sku,
      name: input.name,
      category_slug: input.categorySlug,
      price: { amount: input.priceAmount, currency: "BRL" },
      description: input.description ?? "",
      variants: input.variants,
    }),
  });
}

export function getStockLevel(sku: string): Promise<StockLevel> {
  return apiFetch<StockLevel>(`/api/inventory/${encodeURIComponent(sku)}`);
}

export function receiveStock(sku: string, quantity: number): Promise<StockLevel> {
  return apiFetch<StockLevel>(`/api/inventory/${encodeURIComponent(sku)}/receive`, {
    method: "POST",
    body: JSON.stringify({ quantity }),
  });
}
