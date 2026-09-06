export interface ColorOption {
  value: string;
  label: string;
  available: boolean;
}

export interface ColorSwatchProps {
  options: ColorOption[];
  selected?: string;
  onSelect: (value: string) => void;
}

/** Sem um mapa cor-nome -> valor CSS confiável no domínio hoje (o catálogo
 * guarda o nome da cor como texto livre, ex. "Azul"), o seletor usa pílulas
 * de texto em vez de inventar uma amostra visual que poderia não bater com
 * a cor real. Indisponibilidade é sinalizada por atributo, não só opacidade
 * (ver referencia-frontend-storefront.md, seção 3). */
export function ColorSwatch({ options, selected, onSelect }: ColorSwatchProps) {
  return (
    <div className="color-swatch" role="group" aria-label="Cor">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className="color-swatch__option"
          aria-pressed={option.value === selected}
          aria-disabled={!option.available}
          disabled={!option.available}
          onClick={() => option.available && onSelect(option.value)}
        >
          {option.label}
          {!option.available && <span className="sr-only"> (indisponível)</span>}
        </button>
      ))}
    </div>
  );
}
