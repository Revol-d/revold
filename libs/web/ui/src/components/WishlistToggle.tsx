export interface WishlistToggleProps {
  productName: string;
  isActive: boolean;
  onToggle: () => void;
  className?: string;
}

/** Estado ativo/inativo anunciado por `aria-pressed`, não só a troca visual
 * do ícone (ver referencia-frontend-storefront.md, seção 1). Componente
 * autônomo para reuso fora de ProductCard (ex.: PDP). */
export function WishlistToggle({ productName, isActive, onToggle, className }: WishlistToggleProps) {
  return (
    <button
      type="button"
      className={["wishlist-toggle", className].filter(Boolean).join(" ")}
      aria-pressed={isActive}
      aria-label={
        isActive ? `Remover ${productName} da lista de desejos` : `Adicionar ${productName} à lista de desejos`
      }
      onClick={onToggle}
    >
      <span aria-hidden="true">{isActive ? "♥" : "♡"}</span>
    </button>
  );
}
