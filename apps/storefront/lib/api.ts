/** Cliente HTTP tipado para o api-gateway. Espelha contracts/api/catalog.yaml
 * manualmente por enquanto (mesmo racional de core_catalog/schemas.py no
 * backend) — um gerador de client a partir do OpenAPI pode substituir isso
 * depois sem mudar quem chama estas funções.
 *
 * As duas páginas que usam este arquivo (app/page.tsx e
 * app/collections/[slug]/page.tsx) são Server Components — o fetch roda no
 * servidor do Next.js, dentro do próprio container do storefront, não no
 * navegador. Lá dentro, "localhost:8000" é o container do storefront, não
 * o do api-gateway (cada serviço do docker-compose tem sua própria rede de
 * loopback) — só o navegador do usuário, rodando na máquina host, enxerga
 * api-gateway em localhost:8000 (via port mapping). Por isso o servidor
 * usa o nome do serviço na rede do Docker Compose
 * (API_GATEWAY_INTERNAL_URL=http://api-gateway:8000) e só o navegador usa
 * NEXT_PUBLIC_API_GATEWAY_URL. Se algum dia um Client Component passar a
 * chamar este arquivo, o `typeof window` abaixo já escolhe a URL certa
 * automaticamente. */
const API_BASE =
  typeof window === "undefined"
    ? (process.env.API_GATEWAY_INTERNAL_URL ??
      process.env.NEXT_PUBLIC_API_GATEWAY_URL ??
      "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:8000");

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

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: 60 }, // ISR: catálogo não muda a cada request
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Erro ${response.status} ao chamar ${path}`);
  }
  return response.json() as Promise<T>;
}

export function listCategories(): Promise<Category[]> {
  return apiFetch<Category[]>("/api/catalog/categories");
}

export type ProductSort = "relevance" | "price_asc" | "price_desc";

export function listProducts(params: {
  category?: string;
  q?: string;
  sort?: ProductSort;
  page?: number;
  pageSize?: number;
}): Promise<ProductPage> {
  const query = new URLSearchParams();
  if (params.category) query.set("category", params.category);
  if (params.q) query.set("q", params.q);
  if (params.sort) query.set("sort", params.sort);
  if (params.page) query.set("page", String(params.page));
  if (params.pageSize) query.set("page_size", String(params.pageSize));
  const qs = query.toString();
  return apiFetch<ProductPage>(`/api/catalog/products${qs ? `?${qs}` : ""}`);
}

export function getProduct(sku: string): Promise<Product> {
  return apiFetch<Product>(`/api/catalog/products/${encodeURIComponent(sku)}`);
}

// --- Carrinho (core-cart) ---------------------------------------------
// Estas funções sempre rodam no navegador (chamadas de dentro de Client
// Components), então usam NEXT_PUBLIC_API_GATEWAY_URL diretamente em vez de
// API_BASE — o mesmo cliente HTTP do carrinho nunca roda no servidor do
// Next.js (ver comentário no topo do arquivo sobre por que isso importa).
const BROWSER_API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:8000";

export interface CartItemDTO {
  sku: string;
  name: string;
  variant_label: string;
  unit_price: string;
  quantity: number;
  available_quantity: number | null;
}

export interface CartDTO {
  cart_id: string;
  items: CartItemDTO[];
  total: string;
  currency: string;
}

async function cartFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BROWSER_API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Erro ${response.status} ao chamar ${path}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function getCart(cartId: string): Promise<CartDTO> {
  return cartFetch<CartDTO>(`/api/cart/${encodeURIComponent(cartId)}`);
}

export function addCartItem(
  cartId: string,
  item: { sku: string; name: string; variant_label: string; unit_price: string; quantity?: number },
): Promise<CartDTO> {
  return cartFetch<CartDTO>(`/api/cart/${encodeURIComponent(cartId)}/items`, {
    method: "POST",
    body: JSON.stringify(item),
  });
}

export function updateCartItemQuantity(cartId: string, sku: string, quantity: number): Promise<CartDTO> {
  return cartFetch<CartDTO>(`/api/cart/${encodeURIComponent(cartId)}/items/${encodeURIComponent(sku)}`, {
    method: "PATCH",
    body: JSON.stringify({ quantity }),
  });
}

export function removeCartItem(cartId: string, sku: string): Promise<CartDTO> {
  return cartFetch<CartDTO>(`/api/cart/${encodeURIComponent(cartId)}/items/${encodeURIComponent(sku)}`, {
    method: "DELETE",
  });
}

export interface CheckoutHandoffDTO {
  handoff_url: string;
  provider: string;
}

export function startCheckout(cartId: string): Promise<CheckoutHandoffDTO> {
  return cartFetch<CheckoutHandoffDTO>(`/api/cart/${encodeURIComponent(cartId)}/checkout`, {
    method: "POST",
  });
}

// --- Assistente de IA (core-ai-assistant) ------------------------------
export interface AssistantChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantReplyDTO {
  message: string;
  escalate_to_whatsapp: boolean;
  retrieved_products: { sku: string; name: string }[];
}

export function askAssistant(question: string, history: AssistantChatMessage[]): Promise<AssistantReplyDTO> {
  return cartFetch<AssistantReplyDTO>(`/api/assistant/ask`, {
    method: "POST",
    body: JSON.stringify({ question, history }),
  });
}
