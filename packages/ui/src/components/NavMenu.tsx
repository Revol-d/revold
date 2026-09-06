export interface NavMenuItem {
  label: string;
  href: string;
}

export interface NavMenuProps {
  items: NavMenuItem[];
  currentHref?: string;
}

export function NavMenu({ items, currentHref }: NavMenuProps) {
  return (
    <nav aria-label="Navegação principal" className="nav-menu">
      <ul>
        {items.map((item) => (
          <li key={item.href}>
            <a href={item.href} aria-current={item.href === currentHref ? "page" : undefined}>
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
