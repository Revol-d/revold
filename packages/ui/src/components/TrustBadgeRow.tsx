import type { ReactNode } from "react";

export interface TrustBadge {
  icon: ReactNode;
  label: string;
}

export interface TrustBadgeRowProps {
  badges: TrustBadge[];
}

/** Selo de confiança genérico — o texto de cada selo (política de troca,
 * forma de pagamento, etc.) é decidido por quem consome o componente, nunca
 * fixo aqui (ver referencia-frontend-storefront.md, seção 4: nada
 * específico da Nick dentro de packages/ui). */
export function TrustBadgeRow({ badges }: TrustBadgeRowProps) {
  return (
    <ul className="trust-badge-row">
      {badges.map((badge, index) => (
        <li key={index} className="trust-badge-row__item">
          <span aria-hidden="true">{badge.icon}</span>
          <span>{badge.label}</span>
        </li>
      ))}
    </ul>
  );
}
