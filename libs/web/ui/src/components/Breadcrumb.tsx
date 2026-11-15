export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav aria-label="Trilha de navegação" className="breadcrumb">
      <ol>
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={item.href ?? item.label}>
              {item.href && !isLast ? <a href={item.href}>{item.label}</a> : <span aria-current={isLast ? "page" : undefined}>{item.label}</span>}
              {!isLast && <span aria-hidden="true"> — </span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
