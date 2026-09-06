import type { ReactNode } from "react";

export interface IconButtonProps {
  /** Nome acessível real — nunca deixar só o ícone falar por si (ver achado
   * de bug em referencia-frontend-storefront.md: chave de tradução crua
   * vazando como aria-label em produção). */
  label: string;
  icon: ReactNode;
  onClick?: () => void;
  href?: string;
  badgeCount?: number;
  pressed?: boolean;
  className?: string;
}

/** Botão de ícone genérico do design system — usado por SiteHeader (busca,
 * conta, wishlist, carrinho) e por qualquer outro projeto do monorepo.
 * Renderiza como <a> quando `href` é passado, senão como <button>. */
export function IconButton({
  label,
  icon,
  onClick,
  href,
  badgeCount,
  pressed,
  className,
}: IconButtonProps) {
  const content = (
    <>
      <span aria-hidden="true" className="icon-button__glyph">
        {icon}
      </span>
      {typeof badgeCount === "number" && badgeCount > 0 && (
        <span className="icon-button__badge" aria-hidden="true">
          {badgeCount > 99 ? "99+" : badgeCount}
        </span>
      )}
      <span className="sr-only">
        {label}
        {typeof badgeCount === "number" && badgeCount > 0 ? ` (${badgeCount})` : ""}
      </span>
    </>
  );

  const classes = ["icon-button", className].filter(Boolean).join(" ");

  if (href) {
    return (
      <a href={href} className={classes} aria-label={label}>
        {content}
      </a>
    );
  }

  return (
    <button
      type="button"
      className={classes}
      onClick={onClick}
      aria-label={label}
      aria-pressed={pressed}
    >
      {content}
    </button>
  );
}
