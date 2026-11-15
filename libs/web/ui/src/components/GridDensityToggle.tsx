export type GridDensity = "comfortable" | "compact";

export interface GridDensityToggleProps {
  value: GridDensity;
  onChange: (value: GridDensity) => void;
}

/** Alterna quantas colunas o grid de produtos usa. Estado anunciado por
 * `aria-pressed` em cada opção, não só troca visual do ícone. */
export function GridDensityToggle({ value, onChange }: GridDensityToggleProps) {
  return (
    <div className="grid-density-toggle" role="group" aria-label="Densidade da grade de produtos">
      <button
        type="button"
        aria-pressed={value === "comfortable"}
        aria-label="Grade confortável (menos colunas)"
        onClick={() => onChange("comfortable")}
      >
        <span aria-hidden="true">▦</span>
      </button>
      <button
        type="button"
        aria-pressed={value === "compact"}
        aria-label="Grade compacta (mais colunas)"
        onClick={() => onChange("compact")}
      >
        <span aria-hidden="true">▦▦</span>
      </button>
    </div>
  );
}
