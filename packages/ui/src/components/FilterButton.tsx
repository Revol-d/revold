export interface FilterButtonProps {
  activeCount: number;
  isOpen: boolean;
  onClick: () => void;
}

/** Botão que abre/fecha o FilterPanel — o dono do estado `isOpen` e do
 * painel em si é o app chamador (ex.: um FilterPanel dentro de um popover
 * ou de uma seção da página). */
export function FilterButton({ activeCount, isOpen, onClick }: FilterButtonProps) {
  return (
    <button
      type="button"
      className="filter-button"
      aria-expanded={isOpen}
      aria-controls="filter-panel"
      onClick={onClick}
    >
      Filtrar{activeCount > 0 ? ` (${activeCount})` : ""}
    </button>
  );
}
