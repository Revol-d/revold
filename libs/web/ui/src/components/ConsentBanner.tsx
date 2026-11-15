export interface ConsentBannerProps {
  isVisible: boolean;
  onAcceptAll: () => void;
  onRejectNonEssential: () => void;
  onOpenPreferences?: () => void;
}

/** Banner de consentimento de cookies. A LGPD exige "recusar" tão acessível
 * e visível quanto "aceitar" — os dois botões têm o mesmo peso visual aqui,
 * de propósito (nunca só "aceitar" em destaque com "recusar" escondido; ver
 * referencia-frontend-storefront.md, seções 1 e 3). */
export function ConsentBanner({
  isVisible,
  onAcceptAll,
  onRejectNonEssential,
  onOpenPreferences,
}: ConsentBannerProps) {
  if (!isVisible) return null;

  return (
    <div className="consent-banner" role="region" aria-label="Consentimento de cookies">
      <p>
        Usamos cookies essenciais para o funcionamento da loja (como o carrinho) e cookies
        opcionais para entender como o site é usado. Você pode aceitar todos ou recusar os
        não essenciais a qualquer momento.
      </p>
      <div className="consent-banner__actions">
        <button type="button" className="consent-banner__reject" onClick={onRejectNonEssential}>
          Recusar não essenciais
        </button>
        <button type="button" className="consent-banner__accept" onClick={onAcceptAll}>
          Aceitar todos
        </button>
        {onOpenPreferences && (
          <button type="button" className="consent-banner__preferences" onClick={onOpenPreferences}>
            Preferências
          </button>
        )}
      </div>
    </div>
  );
}
