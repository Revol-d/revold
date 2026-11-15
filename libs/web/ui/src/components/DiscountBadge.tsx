export interface DiscountBadgeProps {
  percentOff: number;
}

export function DiscountBadge({ percentOff }: DiscountBadgeProps) {
  if (percentOff <= 0) return null;
  return <span className="discount-badge">{percentOff}% OFF</span>;
}
