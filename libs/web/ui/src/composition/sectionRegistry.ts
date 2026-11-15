import type { ComponentType } from "react";
import { HeroBanner, type HeroBannerProps } from "../components/HeroBanner";

/** Registro type → componente. Toda seção nova precisa ser adicionada aqui E
 * em types.ts (schema de validação das props). ProductGrid não entra aqui
 * porque depende de dados assíncronos (fetch do catálogo) — é resolvido pelo
 * app (apps/ecommerce/storefront), não por libs/web/ui, que fica agnóstico de fonte de
 * dados. Ver PageRenderer.tsx para como os dois se encaixam. */
// Registro heterogêneo: cada entrada tem seu próprio tipo de props
// (HeroBannerProps hoje, mais tipos conforme o registro cresce) e é
// convertida com "as" no próprio valor (ver HeroBanner abaixo) — não há
// um tipo de props comum entre as seções que não seja `any`/`unknown`
// aqui na declaração do mapa.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const staticSectionRegistry: Record<string, ComponentType<any>> = {
  HeroBanner: HeroBanner as ComponentType<HeroBannerProps>,
};
