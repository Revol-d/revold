import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nick — Painel administrativo",
  description: "Painel interno de operações da loja da Nick",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
