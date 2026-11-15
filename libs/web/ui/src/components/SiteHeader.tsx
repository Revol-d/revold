"use client";
import { useState, type FormEvent, type ReactNode } from "react";
import { NavMenu, type NavMenuItem } from "./NavMenu";
import { IconButton } from "./IconButton";

export interface SiteHeaderProps {
  logo: ReactNode;
  logoHref?: string;
  navItems: NavMenuItem[];
  currentHref?: string;
  searchHref?: string;
  onSearchSubmit?: (query: string) => void;
  wishlistHref?: string;
  wishlistCount?: number;
  cartCount?: number;
  onCartOpen?: () => void;
}

/** Header fixo (sticky via CSS) composto de NavMenu + IconButton — logo,
 * busca, wishlist e carrinho. O menu em telas pequenas é uma revelação
 * simples (button + aria-expanded), sem depender de JS de terceiros.
 * libs/web/ui não conhece a marca: logo, itens de navegação e contadores
 * vêm todos por prop (ver referencia-frontend-storefront.md, seção 4). */
export function SiteHeader({
  logo,
  logoHref = "/",
  navItems,
  currentHref,
  searchHref,
  onSearchSubmit,
  wishlistHref,
  wishlistCount,
  cartCount,
  onCartOpen,
}: SiteHeaderProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearchSubmit?.(searchValue.trim());
  }

  return (
    <header className="site-header">
      <div className="site-header__row">
        <button
          type="button"
          className="site-header__mobile-toggle"
          aria-expanded={mobileOpen}
          aria-controls="site-header-mobile-nav"
          aria-label={mobileOpen ? "Fechar menu de navegação" : "Abrir menu de navegação"}
          onClick={() => setMobileOpen((v) => !v)}
        >
          <span aria-hidden="true">{mobileOpen ? "✕" : "☰"}</span>
        </button>

        <a href={logoHref} className="site-header__logo">
          {logo}
        </a>

        <div className="site-header__nav-desktop">
          <NavMenu items={navItems} currentHref={currentHref} />
        </div>

        <div className="site-header__actions">
          {onSearchSubmit ? (
            <form role="search" className="site-header__search" onSubmit={handleSearchSubmit}>
              <label htmlFor="site-header-search-input" className="sr-only">
                Buscar produtos
              </label>
              <input
                id="site-header-search-input"
                type="search"
                name="q"
                placeholder="Buscar produtos"
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
              />
              <button type="submit" className="site-header__search-submit" aria-label="Buscar">
                <span aria-hidden="true">🔎</span>
              </button>
            </form>
          ) : (
            searchHref && <IconButton label="Buscar" icon={<span>🔎</span>} href={searchHref} />
          )}

          {wishlistHref && (
            <IconButton
              label="Lista de desejos"
              icon={<span>♡</span>}
              href={wishlistHref}
              badgeCount={wishlistCount}
            />
          )}

          <IconButton
            label="Abrir carrinho"
            icon={<span>🛍</span>}
            onClick={onCartOpen}
            badgeCount={cartCount}
          />
        </div>
      </div>

      <div id="site-header-mobile-nav" className="site-header__nav-mobile" hidden={!mobileOpen}>
        <NavMenu items={navItems} currentHref={currentHref} />
      </div>
    </header>
  );
}
