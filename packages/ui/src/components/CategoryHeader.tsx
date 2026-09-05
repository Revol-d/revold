export interface CategoryHeaderProps {
  title: string;
  description?: string;
  resultCount: number;
}

export function CategoryHeader({ title, description, resultCount }: CategoryHeaderProps) {
  return (
    <header className="category-header">
      <h1>{title}</h1>
      {description && <p className="category-header__description">{description}</p>}
      <p className="category-header__count" aria-live="polite">
        {resultCount} {resultCount === 1 ? "produto" : "produtos"}
      </p>
    </header>
  );
}
