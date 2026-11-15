/** Rodapé simples — texto deliberadamente modesto: o modelo de negócio da
 * Nick ainda é atendimento manual por WhatsApp (ADR-0005), então nada aqui
 * promete prazo de frete ou política de troca que ainda não foi decidida. */
export function SiteFooter() {
  return (
    <footer className="site-footer">
      <p>Nick — peças pensadas para o seu dia a dia.</p>
      <p>Pagamento e envio combinados diretamente com a Nick pelo WhatsApp.</p>
      <p className="site-footer__copyright">© {new Date().getFullYear()} Nick.</p>
    </footer>
  );
}
