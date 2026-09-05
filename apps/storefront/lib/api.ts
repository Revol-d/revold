/** Cliente HTTP tipado para o api-gateway. Espelha contracts/api/catalog.yaml
 * manualmente por enquanto (mesmo racional de core_catalog/schemas.py no
 * backend) — um gerador de client a partir do OpenAPI pode substituir isso
 * depois sem mudar quem chama estas funções. */

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:8000";

export interface Money {
  amount: string;
  currency: string;
}

export interface ProductVariant {
  sku: string;
  size: string;
  color: string;
  in_stock: boolean;
}

export interface Category {
  slug: string;
  name: string;
}

export interface Product {
  sku: string;
  name: string;
  description: string;
  category: Category;
  price: Money;
  original_price: Money | null;
  variants: ProductVariant[];
  images: string[];
}

export interface ProductPage {
  items: Product[];
  page: number;
  page_size: number;
  total: number;
}

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: 60 }, // ISR: catálogo não muda a cada request
  });
  if (!response.ok) {
    throw new Error(`Erro ${response.status} ao chamar ${path}`);
  }
  return response.json() as Promise<T>;
}

export function listCategories(): Promise<Category[]> {
  return apiFetch<Category[]>("/api/catalog/categories");
}

export function listProducts(params: {
  category?: string;
  page?: number;
  pageSize?: number;
}): Promise<ProductPage> {
  const query = new URLSearchParams();
  if (params.category) query.set("category", params.category);
  if (params.page) query.set("page", String(params.page));
  if (params.pageSize) query.set("page_size", String(params.pageSize));
  const qs = query.toString();
  return apiFetch<ProductPage>(`/api/catalog/products${qs ? `?${qs}` : ""}`);
}

export function getProduct(sku: string): Promise<Product> {
  return apiFetch<Product>(`/api/catalog/products/${encodeURIComponent(sku)}`);
}
