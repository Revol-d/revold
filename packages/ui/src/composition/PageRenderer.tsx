import type { ReactNode } from "react";
import type { Section } from "./types";
import { staticSectionRegistry } from "./sectionRegistry";

export interface PageRendererProps {
  sections: Section[];
  /** Seções que precisam de dado assíncrono (ex. ProductGrid) são resolvidas
   * pelo app chamador e passadas aqui já como nó React, indexadas por posição
   * na lista de sections. packages/ui não faz fetch — mantém o design system
   * puro (ver ADR-0002/ADR-0007). */
  renderDynamicSection?: (section: Section, index: number) => ReactNode | undefined;
}

/** Monta uma página a partir de uma composição declarativa (dado), não de
 * JSX escrito à mão por página. Trocar o layout é editar a lista de
 * `sections` (arquivo em apps/storefront/content/pages/*.ts) — uma edição
 * estruturada que um prompt resolve com precisão. */
export function PageRenderer({ sections, renderDynamicSection }: PageRendererProps) {
  return (
    <>
      {sections.map((section, index) => {
        const dynamic = renderDynamicSection?.(section, index);
        if (dynamic !== undefined) {
          return <div key={index}>{dynamic}</div>;
        }
        const Component = staticSectionRegistry[section.type];
        if (!Component) {
          if (process.env.NODE_ENV !== "production") {
            console.warn(`PageRenderer: seção desconhecida "${section.type}"`);
          }
          return null;
        }
        return <Component key={index} {...section.props} />;
      })}
    </>
  );
}
