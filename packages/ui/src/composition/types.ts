import { z } from "zod";

/** Um section descriptor é dado puro: { type, props }. A página inteira é uma
 * lista deles (ver home.ts em apps/storefront/content/pages). Mudar o layout
 * de uma página é editar esta lista — não é preciso escrever JSX novo nem
 * abrir uma ferramenta de design (ver ADR-0007). */
export const heroBannerPropsSchema = z.object({
  title: z.string(),
  subtitle: z.string().optional(),
  imageUrl: z.string().url(),
  imageAlt: z.string(),
  ctaLabel: z.string().optional(),
  ctaHref: z.string().optional(),
});

export const productGridPropsSchema = z.object({
  title: z.string().optional(),
  categorySlug: z.string().optional(),
  limit: z.number().int().positive().max(48).default(12),
});

export const sectionSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("HeroBanner"), props: heroBannerPropsSchema }),
  z.object({ type: z.literal("ProductGrid"), props: productGridPropsSchema }),
]);

export type Section = z.infer<typeof sectionSchema>;
export const pageCompositionSchema = z.array(sectionSchema);
export type PageComposition = z.infer<typeof pageCompositionSchema>;
