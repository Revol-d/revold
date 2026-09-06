import type { Metadata } from "next";
import dynamic from "next/dynamic";
import "./globals.css";
import { Providers } from "./providers";
import { SiteHeaderContainer } from "@/components/SiteHeaderContainer";
import { CartDrawerContainer } from "@/components/CartDrawerContainer";
import { ConsentBannerContainer } from "@/components/ConsentBannerContainer";
import { SiteFooter } from "@/components/SiteFooter";
import { listCategories } from "@/lib/api";

export const metadata: Metadata = {
  title: "Nick — Loja",
  description: "E-commerce da Nick",
};

// Carregado só no navegador e via dynamic import — o assistente de IA não
// deve pesar o carregamento inicial da página (ver
// referencia-frontend-storefront.md, seção 1).
const ChatWidgetContainer = dynamic(
  () => import("@/components/ChatWidgetContainer").then((m) => m.ChatWidgetContainer),
  { ssr: false },
);

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Categorias vêm do servidor (Server Component) e descem como prop pro
  // header client — o header em si não faz fetch, só recebe dado pronto.
  let categories: { slug: string; name: string }[] = [];
  try {
    categories = await listCategories();
  } catch {
    // Se o catálogo estiver fora do ar, a navegação degrada pra só "Home"
    // em vez de derrubar a página inteira.
    categories = [];
  }
  const navItems = [
    { label: "Todas as categorias", href: "/collections" },
    ...categories.map((c) => ({ label: c.name, href: `/collections/${c.slug}` })),
  ];

  return (
    <html lang="pt-BR">
      <body>
        <a href="#main-content" className="sr-only">
          Pular para o conteúdo principal
        </a>
        <Providers>
          <SiteHeaderContainer navItems={navItems} />
          {children}
          <SiteFooter />
          <CartDrawerContainer />
          <ConsentBannerContainer />
          <ChatWidgetContainer />
        </Providers>
      </body>
    </html>
  );
}
