"use client";
import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

/** TanStack Query para estado remoto (carrinho, e futuramente qualquer
 * outra leitura/mutação client-side) — ver README/referencia-frontend, seção
 * 2. Um QueryClient por sessão de navegador (useState garante que não é
 * recriado a cada render, e nem compartilhado entre requisições SSR de
 * usuários diferentes). */
export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
