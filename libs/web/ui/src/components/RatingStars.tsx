export interface RatingStarsProps {
  value: number; // 0-5
  count: number;
}

/** Estrelas são decorativas; o valor real vai em texto para leitor de tela. */
export function RatingStars({ value, count }: RatingStarsProps) {
  return (
    <span className="rating-stars" role="img" aria-label={`Avaliação ${value.toFixed(1)} de 5, ${count} avaliações`}>
      <span aria-hidden="true">{"★".repeat(Math.round(value))}{"☆".repeat(5 - Math.round(value))}</span>
    </span>
  );
}
