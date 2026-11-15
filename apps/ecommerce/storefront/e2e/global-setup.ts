/**
 * Seed de dados pro E2E (ADR-0020): roda antes da suíte inteira, contra o
 * api-gateway real (Postgres/Redis reais, sem mock) — os mesmos passos que
 * a Nick faria no admin-dashboard: logar (AUTH_PROVIDER=dev, ver
 * dev_provider.py, dá papel ADMIN instantâneo em ambiente de
 * desenvolvimento), criar categoria + produto com uma variante, dar
 * entrada de estoque nela. Idempotente: pode rodar de novo sem duplicar
 * (checa antes de criar, tolera 409).
 */
import type { FullConfig } from "@playwright/test";

const API_BASE = process.env.E2E_API_BASE_URL ?? "http://localhost:8000";

export const E2E_CATEGORY_SLUG = "e2e-camisetas";
export const E2E_PRODUCT_SKU = "TSHIRT-E2E";
export const E2E_VARIANT_SKU = "TSHIRT-E2E-M-AZUL";
export const E2E_PRODUCT_NAME = "Camiseta E2E";

async function waitForHealth(timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError: unknown;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${API_BASE}/health`);
      if (response.ok) return;
    } catch (err) {
      lastError = err;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`api-gateway não respondeu /health em ${timeoutMs}ms: ${String(lastError)}`);
}

function parseSessionCookie(setCookieHeader: string | null): string {
  if (!setCookieHeader) {
    throw new Error("login/complete não devolveu Set-Cookie — sessão não foi criada");
  }
  const match = setCookieHeader.match(/session_id=([^;]+)/);
  if (!match) {
    throw new Error(`Set-Cookie sem session_id: ${setCookieHeader}`);
  }
  return match[1];
}

async function loginAsDevAdmin(): Promise<string> {
  const startResponse = await fetch(`${API_BASE}/api/auth/login/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ redirect_uri: "http://localhost:3001/callback" }),
  });
  if (!startResponse.ok) {
    throw new Error(`login/start falhou: ${startResponse.status}`);
  }
  const { state } = (await startResponse.json()) as { state: string };

  const completeResponse = await fetch(`${API_BASE}/api/auth/login/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: "dev", state }),
  });
  if (!completeResponse.ok) {
    throw new Error(`login/complete falhou: ${completeResponse.status}`);
  }
  return parseSessionCookie(completeResponse.headers.get("set-cookie"));
}

async function ensureCategory(sessionCookie: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/catalog/categories`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Cookie: `session_id=${sessionCookie}` },
    body: JSON.stringify({ slug: E2E_CATEGORY_SLUG, name: "Camisetas (E2E)" }),
  });
  if (!response.ok && response.status !== 409) {
    throw new Error(`Falha ao criar categoria de seed: ${response.status} ${await response.text()}`);
  }
}

async function ensureProduct(sessionCookie: string): Promise<void> {
  const existing = await fetch(
    `${API_BASE}/api/catalog/products/${encodeURIComponent(E2E_PRODUCT_SKU)}`
  );
  if (existing.status === 200) return;

  const response = await fetch(`${API_BASE}/api/catalog/products`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Cookie: `session_id=${sessionCookie}` },
    body: JSON.stringify({
      sku: E2E_PRODUCT_SKU,
      name: E2E_PRODUCT_NAME,
      category_slug: E2E_CATEGORY_SLUG,
      price: { amount: "99.90", currency: "BRL" },
      description: "Produto de seed usado só pelo teste E2E (ver e2e/global-setup.ts).",
      variants: [
        { sku: E2E_VARIANT_SKU, size: "M", color: "Azul", in_stock: true },
      ],
    }),
  });
  if (!response.ok && response.status !== 409) {
    throw new Error(`Falha ao criar produto de seed: ${response.status} ${await response.text()}`);
  }
}

async function ensureStock(sessionCookie: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/inventory/${encodeURIComponent(E2E_VARIANT_SKU)}/receive`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: `session_id=${sessionCookie}` },
      body: JSON.stringify({ quantity: 50 }),
    }
  );
  if (!response.ok) {
    throw new Error(`Falha ao dar entrada de estoque de seed: ${response.status} ${await response.text()}`);
  }
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  await waitForHealth(60_000);
  const sessionCookie = await loginAsDevAdmin();
  await ensureCategory(sessionCookie);
  await ensureProduct(sessionCookie);
  await ensureStock(sessionCookie);
}
