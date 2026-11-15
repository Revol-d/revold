export type SortValue = "relevance" | "price_asc" | "price_desc";

export interface SortSelectProps {
  value: SortValue;
  onChange: (value: SortValue) => void;
}

const OPTIONS: { value: SortValue; label: string }[] = [
  { value: "relevance", label: "Mais relevantes" },
  { value: "price_asc", label: "Menor preço" },
  { value: "price_desc", label: "Maior preço" },
];

/** Ordenação funciona via query param (o app lê/escreve a URL a partir de
 * onChange) — permite link compartilhável e botão voltar do navegador (ver
 * referencia-frontend-storefront.md, seção 1). */
export function SortSelect({ value, onChange }: SortSelectProps) {
  return (
    <div className="sort-select">
      <label htmlFor="sort-select-input">Ordenar por</label>
      <select
        id="sort-select-input"
        value={value}
        onChange={(e) => onChange(e.target.value as SortValue)}
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
