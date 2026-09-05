import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nick — Loja",
  description: "E-commerce da Nick",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <a href="#main-content" className="sr-only">
          Pular para o conteúdo principal
        </a>
        {children}
      </body>
    </html>
  );
}
