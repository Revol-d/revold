"use client";

import { useEffect } from "react";

/**
 * Boundary de erro do App Router — sem isto, um 500 de qualquer chamada
 * de API (configurações da loja, estoque, catálogo) derrubava a tela
 * inteira do admin-dashboard sem nenhuma mensagem amigável pra Nick/staff.
 */
export default function AdminDashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console -- traceback real já foi pro
    // log do api-gateway; isto é só o que chega ao console do navegador.
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-xl font-semibold">Não foi possível carregar esta tela</h1>
      <p className="text-slate-600">
        Pode ser algo temporário no servidor. Tenta de novo em alguns instantes.
      </p>
      <button
        type="button"
        onClick={() => reset()}
        className="rounded-md bg-slate-900 px-4 py-2 text-white"
      >
        Tentar novamente
      </button>
    </main>
  );
}
