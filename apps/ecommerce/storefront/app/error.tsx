"use client";

import { useEffect } from "react";

/**
 * Boundary de erro do App Router (Next.js) — pega qualquer exceção não
 * tratada localmente em uma página (ex.: a API do catálogo fora do ar) e
 * mostra isto em vez do overlay de erro do Next.js (só aparece em dev) ou
 * da tela de erro genérica dele em produção. Sem isto, nenhuma página do
 * storefront tinha rede de segurança — um 500 numa chamada de API
 * derrubava a página inteira, sem nada amigável no lugar.
 *
 * Continua sendo o último recurso, não o primeiro: onde faz sentido (ver
 * `listCategories()` em layout.tsx e a lista de produtos relacionados em
 * products/[sku]/page.tsx), a página trata o erro localmente e degrada só
 * aquele pedaço — este boundary cobre o que não foi tratado localmente,
 * geralmente porque não há nada para renderizar sem aquele dado (ex.: a
 * lista principal de produtos de /collections).
 */
export default function StorefrontError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console -- só isto chega ao console do
    // navegador; o traceback de verdade já foi pro log do api-gateway.
    console.error(error);
  }, [error]);

  return (
    <main className="route-error">
      <div className="route-error__card">
        <h1>Não conseguimos carregar esta página</h1>
        <p>
          Pode ser algo temporário do nosso lado. Tenta de novo — se continuar acontecendo, fala com a
          gente pelo WhatsApp.
        </p>
        <button type="button" onClick={() => reset()} className="route-error__retry">
          Tentar novamente
        </button>
      </div>
    </main>
  );
}
