import { defineConfig, devices } from "@playwright/test";

/**
 * Configuração de teste E2E (ADR-0012 previa a camada, nunca implementada
 * — ver docs/kb/decisoes/0020-testes-e2e-playwright.md). Cobre o
 * fluxo real de cliente ponta a ponta: navegar pelo catálogo, adicionar ao
 * carrinho, ir a checkout e confirmar o handoff pro WhatsApp (ADR-0005) —
 * sem mockar nada, contra api-gateway + Postgres + Redis reais.
 *
 * Roda na máquina (ou no runner do CI), contra a pilha do `docker compose`
 * já de pé: a loja em E2E_BASE_URL e a API em E2E_API_BASE_URL (padrão
 * localhost:3000 e localhost:8000). O navegador é o que o
 * `playwright install chromium` baixou; PLAYWRIGHT_CHROMIUM_PATH só serve
 * para apontar um Chromium já instalado, em ambiente sem acesso à rede.
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
        // Sem a variável, o Playwright usa o Chromium que ele mesmo instalou. O padrão
        // antigo (`/opt/pw-browsers/chromium`) era do ambiente em que estes testes foram
        // escritos e não existe em mais lugar nenhum.
        ...(process.env.PLAYWRIGHT_CHROMIUM_PATH
          ? { launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } }
          : {}),
      },
    },
  ],
});
