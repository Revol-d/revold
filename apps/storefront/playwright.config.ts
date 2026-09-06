import { defineConfig, devices } from "@playwright/test";

/**
 * Configuração de teste E2E (ADR-0012 previa a camada, nunca implementada
 * — ver docs/architecture/adr/0020-testes-e2e-playwright.md). Cobre o
 * fluxo real de cliente ponta a ponta: navegar pelo catálogo, adicionar ao
 * carrinho, ir a checkout e confirmar o handoff pro WhatsApp (ADR-0005) —
 * sem mockar nada, contra api-gateway + Postgres + Redis reais.
 *
 * `executablePath` aponta pro Chromium já instalado no ambiente de CI/dev
 * (variável PLAYWRIGHT_BROWSERS_PATH) em vez de deixar o Playwright baixar
 * um binário — evita depender de rede pra rodar `make test-e2e`.
 */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH ?? "/opt/pw-browsers/chromium",
        },
      },
    },
  ],
});
