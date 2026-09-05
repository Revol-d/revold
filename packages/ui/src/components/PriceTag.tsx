export interface PriceTagProps {
  amount: string;
  currency?: string;
  originalAmount?: string;
  locale?: string;
}

function formatMoney(amount: string, currency: string, locale: string): string {
  const value = Number(amount);
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(value);
}

/** Preço com desconto: mostra o valor original riscado E em texto (não só cor/estilo),
 * para não depender só de percepção visual (acessibilidade). */
export function PriceTag({ amount, currency = "BRL", originalAmount, locale = "pt-BR" }: PriceTagProps) {
  const hasDiscount = Boolean(originalAmount && originalAmount !== amount);
  return (
    <span className="price-tag">
      <span className="price-tag__current">{formatMoney(amount, currency, locale)}</span>
      {hasDiscount && (
        <>
          <span className="price-tag__original" aria-hidden="true">
            {formatMoney(originalAmount as string, currency, locale)}
          </span>
          <span className="sr-only">
            {" "}(preço original {formatMoney(originalAmount as string, currency, locale)})
          </span>
        </>
      )}
    </span>
  );
}
