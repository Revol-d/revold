export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterGroup {
  id: string;
  label: string;
  options: FilterOption[];
}

export interface FilterPanelProps {
  groups: FilterGroup[];
  /** valores selecionados por grupo (id do grupo -> lista de values) */
  selected: Record<string, string[]>;
  onChange: (groupId: string, values: string[]) => void;
  onClear: () => void;
}

/** Painel de filtros por checkbox — cada grupo é uma `fieldset` com
 * `legend`, navegável nativamente por teclado. Quem decide como aplicar os
 * valores selecionados (query param, filtro client-side) é o app chamador. */
export function FilterPanel({ groups, selected, onChange, onClear }: FilterPanelProps) {
  function toggle(groupId: string, value: string) {
    const current = selected[groupId] ?? [];
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    onChange(groupId, next);
  }

  return (
    <div className="filter-panel">
      {groups.map((group) => (
        <fieldset key={group.id} className="filter-panel__group">
          <legend>{group.label}</legend>
          {group.options.map((option) => {
            const checked = (selected[group.id] ?? []).includes(option.value);
            return (
              <label key={option.value} className="filter-panel__option">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggle(group.id, option.value)}
                />
                {option.label}
              </label>
            );
          })}
        </fieldset>
      ))}
      <button type="button" className="filter-panel__clear" onClick={onClear}>
        Limpar filtros
      </button>
    </div>
  );
}
