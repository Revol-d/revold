export interface HeroBannerProps {
  title: string;
  subtitle?: string;
  imageUrl: string;
  imageAlt: string;
  ctaLabel?: string;
  ctaHref?: string;
}

/** Overlay sólido atrás do texto — nunca confiar em contraste da foto em si (ver
 * referencia-frontend-storefront.md, seção 3). */
export function HeroBanner({ title, subtitle, imageUrl, imageAlt, ctaLabel, ctaHref }: HeroBannerProps) {
  return (
    <section className="hero-banner">
      <img src={imageUrl} alt={imageAlt} className="hero-banner__image" />
      <div className="hero-banner__overlay">
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
        {ctaLabel && ctaHref && (
          <a href={ctaHref} className="hero-banner__cta">
            {ctaLabel}
          </a>
        )}
      </div>
    </section>
  );
}
