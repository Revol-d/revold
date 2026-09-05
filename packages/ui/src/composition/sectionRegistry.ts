import type { ComponentType } from "react";
import { HeroBanner, type HeroBannerProps } from "../components/HeroBanner";

/** Registro type → componente. Toda seção nova precisa ser adicionada aqui E
 * em types.ts (schema de validação das props). ProductGrid não entra aqui
 * porque depende de dados assíncronos (fetch do catálogo) — é resolvido pelo
 * app (apps/storefront), não por packages/ui, que fica agnóstico de fonte de
 * dados. Ver PageRenderer.tsx para como os dois se encaixam. */
export const staticSectionRegistry: Record<string, ComponentType<any>> = {
  HeroBanner: HeroBanner as ComponentType<HeroBannerProps>,
};
