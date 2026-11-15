import { expect, test } from "@playwright/test";
import { E2E_PRODUCT_NAME, E2E_PRODUCT_SKU } from "./global-setup";

/**
 * Cobre o fluxo real de cliente ponta a ponta (ADR-0005, ADR-0020):
 * navegar pelo catálogo → abrir um produto → adicionar ao carrinho →
 * fechar o pedido → confirmar que o handoff pro WhatsApp foi gerado com o
 * produto certo. Roda contra o storefront + api-gateway + Postgres/Redis
 * reais (o produto usado aqui é semeado por global-setup.ts).
 */
/** Descarta o banner de cookies (ConsentBannerContainer) clicando "Aceitar
 * todos" — mesma primeira ação que qualquer visitante real faria. Sem
 * isso, o banner (fixo na base da tela) intercepta clique em qualquer
 * botão que fique atrás dele, como o de fechar pedido no drawer do
 * carrinho — um achado real ao rodar este teste pela primeira vez contra
 * um navegador de verdade, não um problema do teste em si. */
async function acceptCookies(page: import("@playwright/test").Page): Promise<void> {
  const acceptButton = page.getByRole("button", { name: "Aceitar todos" });
  if (await acceptButton.isVisible().catch(() => false)) {
    await acceptButton.click();
  }
}

test("cliente navega, adiciona ao carrinho e fecha pedido pelo WhatsApp", async ({ page }) => {
  await page.goto("/collections/all");
  await acceptCookies(page);

  const productLink = page.locator(`a[href="/products/${E2E_PRODUCT_SKU}"]`);
  await expect(productLink).toBeVisible();
  await productLink.click();

  await expect(page).toHaveURL(`/products/${E2E_PRODUCT_SKU}`);
  await expect(page.getByRole("heading", { name: E2E_PRODUCT_NAME })).toBeVisible();

  // A PDP é um Client Component (ProductVariantPicker/AddToCartButton) —
  // o HTML da primeira renderização já chega do servidor, mas o clique só
  // dispara a mutação depois que o React hidrata e liga o onClick. Espera
  // a rede ficar ociosa (bundle de hidratação do Next.js dev já carregado)
  // antes de interagir, senão o clique corre risco de acontecer num botão
  // ainda sem handler (efeito só visível fora de um ambiente com cache
  // "quente" de compilação do Next dev).
  await page.waitForLoadState("networkidle");

  const addToCartButton = page.getByRole("button", { name: "Adicionar ao carrinho" });
  await expect(addToCartButton).toBeEnabled();

  const [addItemResponse] = await Promise.all([
    page.waitForResponse(
      (res) => res.url().includes("/api/cart/") && res.url().endsWith("/items") && res.request().method() === "POST"
    ),
    addToCartButton.click(),
  ]);
  expect(addItemResponse.ok()).toBe(true);

  // O drawer abre sozinho depois de adicionar (ver AddToCartButton.tsx) —
  // confirma que a linha do produto certo está no carrinho antes de seguir.
  const cartDrawer = page.getByRole("dialog", { name: "Carrinho de compras" });
  await expect(cartDrawer.locator(".cart-drawer__item-name", { hasText: E2E_PRODUCT_NAME })).toBeVisible();

  const checkoutButton = cartDrawer.getByRole("button", { name: "Fechar pedido pelo WhatsApp" });
  await expect(checkoutButton).toBeEnabled();

  // A fonte de verdade pro conteúdo do handoff é a resposta da própria
  // API (o texto da mensagem é montado no backend, ver
  // WhatsAppClickToChatCheckout.build_handoff) — checar o JSON evita
  // depender de wa.me carregar de verdade (este ambiente de sandbox não
  // tem saída de rede pro WhatsApp; num CI com internet real, funcionaria
  // igual). Ainda assim confirma que o clique de fato abriu um popup —
  // window.open é o comportamento real que a Nick recebe.
  const [popup, checkoutResponse] = await Promise.all([
    page.waitForEvent("popup"),
    page.waitForResponse(
      (res) => res.url().endsWith("/checkout") && res.request().method() === "POST"
    ),
    checkoutButton.click(),
  ]);
  expect(checkoutResponse.ok()).toBe(true);
  const { handoff_url: handoffUrl, provider } = (await checkoutResponse.json()) as {
    handoff_url: string;
    provider: string;
  };
  expect(provider).toBe("whatsapp-clicktochat");
  expect(handoffUrl).toContain("https://wa.me/");
  expect(decodeURIComponent(handoffUrl)).toContain(E2E_PRODUCT_NAME);
  await popup.close();
});

test("busca por nome do produto encontra o produto semeado (ADR-0014)", async ({ page }) => {
  // Exercita a busca full-text (tsvector + unaccent) de ponta a ponta —
  // não só a query de repositório isolada (já coberta por teste de
  // integração em core-catalog), mas o caminho completo até a PLP.
  await page.goto("/search?q=Camiseta E2E");

  const productLink = page.locator(`a[href="/products/${E2E_PRODUCT_SKU}"]`);
  await expect(productLink).toBeVisible();
});
