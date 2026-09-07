import { notFound } from "next/navigation";
import {
  Accordion,
  Breadcrumb,
  PriceTag,
  ProductGallery,
  RelatedProductsCarousel,
  TrustBadgeRow,
} from "@revold/ui";
import { ApiError, getProduct, listProducts } from "@/lib/api";
import { ProductVariantPicker } from "@/components/ProductVariantPicker";
import { CrossSellContainer } from "@/components/CrossSellContainer";

export const dynamic = "force-dynamic";

interface ProductPageProps {
  params: { sku: string };
}

export default async function ProductDetailPage({ params }: ProductPageProps) {
  let product;
  try {
    product = await getProduct(params.sku);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  // Produtos relacionados são complementares, não o motivo de a página
  // existir — se o catálogo falhar só nesta segunda chamada, o produto
  // principal (já carregado acima) continua exibido normalmente, só sem
  // "combine com"/"você também pode gostar" (mesmo princípio de
  // listCategories() em layout.tsx).
  let related: Awaited<ReturnType<typeof listProducts>>["items"] = [];
  try {
    const relatedPage = await listProducts({ category: product.category.slug, pageSize: 9 });
    related = relatedPage.items.filter((p) => p.sku !== product.sku).slice(0, 8);
  } catch {
    related = [];
  }
  const crossSellCandidates = related
    .filter((p) => p.variants.length === 0 || p.variants.some((v) => v.in_stock))
    .slice(0, 3);

  return (
    <main id="main-content" className="product-detail-page">
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: product.category.name, href: `/collections/${product.category.slug}` },
          { label: product.name },
        ]}
      />

      <div className="product-detail-page__layout">
        <ProductGallery images={product.images} productName={product.name} />

        <div className="product-detail-page__info">
          <h1>{product.name}</h1>
          <PriceTag
            amount={product.price.amount}
            originalAmount={product.original_price?.amount}
            currency={product.price.currency}
          />
          {product.description && <p className="product-detail-page__description">{product.description}</p>}

          <ProductVariantPicker product={product} />

          <TrustBadgeRow
            badges={[
              { icon: "💬", label: "Atendimento e pagamento combinados pelo WhatsApp" },
              { icon: "📦", label: "Envio combinado direto com a Nick" },
              { icon: "🔁", label: "Troca por combinação — fale com a Nick" },
            ]}
          />

          <Accordion
            items={[
              {
                id: "detalhes",
                title: "Detalhes do produto",
                content: <p>{product.description || "Sem descrição adicional para este produto."}</p>,
              },
              {
                id: "pagamento-envio",
                title: "Pagamento e envio",
                content: (
                  <p>
                    O fechamento do pedido acontece pelo WhatsApp: depois de montar o carrinho, clique em
                    &ldquo;Fechar pedido pelo WhatsApp&rdquo; para combinar forma de pagamento e envio
                    diretamente com a Nick.
                  </p>
                ),
              },
              {
                id: "atendimento",
                title: "Dúvidas antes de comprar?",
                content: (
                  <p>Use o assistente no canto da tela para perguntar sobre tamanho, cor ou disponibilidade.</p>
                ),
              },
            ]}
          />
        </div>
      </div>

      <CrossSellContainer title="Combine com" products={crossSellCandidates} />

      <RelatedProductsCarousel
        title="Você também pode gostar"
        products={related.map((p) => ({
          sku: p.sku,
          name: p.name,
          imageUrl: p.images[0] ?? "",
          imageAlt: p.name,
          price: p.price.amount,
          originalPrice: p.original_price?.amount,
          currency: p.price.currency,
          href: `/products/${p.sku}`,
        }))}
      />
    </main>
  );
}
