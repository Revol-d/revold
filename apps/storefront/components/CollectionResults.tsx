"use client";
import { useMemo, useState } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import {
  SortSelect,
  GridDensityToggle,
  FilterButton,
  FilterPanel,
  type SortValue,
  type GridDensity,
  type FilterGroup,
} from "@revold/ui";
import type { Product } from "@/lib/api";
import { ProductGrid } from "@/components/ProductGrid";

export interface CollectionResultsProps {
  /** Já filtrados pelo servidor (categoria + busca + size/color + página). */
  products: Product[];
  /** Mesma categoria/busca, sem o filtro de size/color — só usados para
   * descobrir quais opções mostrar no FilterPanel (ver comentário na page). */
  facetProducts: Product[];
  sort: SortValue;
  sizes: string[];
  colors: string[];
}

/** Tamanho/cor agora são resolvidos no servidor via query param (?size=P,M),
 * do mesmo jeito que sort e busca já eram — link compartilhável, botão
 * voltar do navegador funciona, e o filtro vale pro catálogo inteiro, não
 * só pelos itens já carregados na página atual (limitação anterior). */
export function CollectionResults({
  products,
  facetProducts,
  sort,
  sizes,
  colors,
}: CollectionResultsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [density, setDensity] = useState<GridDensity>("comfortable");
  const [isFilterOpen, setFilterOpen] = useState(false);

  const filterGroups: FilterGroup[] = useMemo(() => {
    const availableSizes = new Set<string>();
    const availableColors = new Set<string>();
    for (const product of facetProducts) {
      for (const variant of product.variants) {
        availableSizes.add(variant.size);
        availableColors.add(variant.color);
      }
    }
    return [
      {
        id: "size",
        label: "Tamanho",
        options: [...availableSizes].sort().map((s) => ({ value: s, label: s })),
      },
      {
        id: "color",
        label: "Cor",
        options: [...availableColors].sort().map((c) => ({ value: c, label: c })),
      },
    ].filter((group) => group.options.length > 0);
  }, [facetProducts]);

  const selected: Record<string, string[]> = { size: sizes, color: colors };

  function updateParam(name: "sort" | "size" | "color", value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(name, value);
    else params.delete(name);
    params.delete("page");
    router.push(`${pathname}?${params.toString()}`);
  }

  function updateSort(value: SortValue) {
    updateParam("sort", value);
  }

  function updateFilter(groupId: string, values: string[]) {
    if (groupId === "size" || groupId === "color") {
      updateParam(groupId, values.join(","));
    }
  }

  function clearFilters() {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("size");
    params.delete("color");
    params.delete("page");
    router.push(`${pathname}?${params.toString()}`);
  }

  const activeFilterCount = sizes.length + colors.length;

  return (
    <div>
      <div className="collection-toolbar">
        <SortSelect value={sort} onChange={updateSort} />
        {filterGroups.length > 0 && (
          <FilterButton
            activeCount={activeFilterCount}
            isOpen={isFilterOpen}
            onClick={() => setFilterOpen((v) => !v)}
          />
        )}
        <GridDensityToggle value={density} onChange={setDensity} />
      </div>

      {isFilterOpen && filterGroups.length > 0 && (
        <div id="filter-panel">
          <FilterPanel
            groups={filterGroups}
            selected={selected}
            onChange={updateFilter}
            onClear={clearFilters}
          />
        </div>
      )}

      <ProductGrid products={products} compact={density === "compact"} />
      {products.length === 0 && <p>Nenhum produto encontrado com esses filtros.</p>}
    </div>
  );
}
