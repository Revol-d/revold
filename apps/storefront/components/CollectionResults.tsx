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
  products: Product[];
  sort: SortValue;
}

/** Filtro por tamanho/cor é aplicado só sobre os produtos já carregados
 * nesta página — o backend ainda não expõe facetas de variante em
 * /api/catalog/products (só category, q e sort). É uma limitação conhecida:
 * "aplicar filtro" aqui não busca mais produtos no servidor, só restringe o
 * que já veio. Ordenação e busca, por outro lado, já são resolvidas no
 * servidor via query param (compartilháveis por link). */
export function CollectionResults({ products, sort }: CollectionResultsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [density, setDensity] = useState<GridDensity>("comfortable");
  const [isFilterOpen, setFilterOpen] = useState(false);
  const [selected, setSelected] = useState<Record<string, string[]>>({});

  const filterGroups: FilterGroup[] = useMemo(() => {
    const sizes = new Set<string>();
    const colors = new Set<string>();
    for (const product of products) {
      for (const variant of product.variants) {
        sizes.add(variant.size);
        colors.add(variant.color);
      }
    }
    return [
      { id: "size", label: "Tamanho", options: [...sizes].sort().map((s) => ({ value: s, label: s })) },
      { id: "color", label: "Cor", options: [...colors].sort().map((c) => ({ value: c, label: c })) },
    ].filter((group) => group.options.length > 0);
  }, [products]);

  const filteredProducts = useMemo(() => {
    const sizeFilter = selected.size ?? [];
    const colorFilter = selected.color ?? [];
    if (sizeFilter.length === 0 && colorFilter.length === 0) return products;
    return products.filter((product) =>
      product.variants.some(
        (variant) =>
          (sizeFilter.length === 0 || sizeFilter.includes(variant.size)) &&
          (colorFilter.length === 0 || colorFilter.includes(variant.color)),
      ),
    );
  }, [products, selected]);

  function updateSort(value: SortValue) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("sort", value);
    params.delete("page");
    router.push(`${pathname}?${params.toString()}`);
  }

  const activeFilterCount = Object.values(selected).reduce((sum, values) => sum + values.length, 0);

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
            onChange={(groupId, values) => setSelected((current) => ({ ...current, [groupId]: values }))}
            onClear={() => setSelected({})}
          />
        </div>
      )}

      <ProductGrid products={filteredProducts} compact={density === "compact"} />
      {filteredProducts.length === 0 && <p>Nenhum produto encontrado com esses filtros.</p>}
    </div>
  );
}
