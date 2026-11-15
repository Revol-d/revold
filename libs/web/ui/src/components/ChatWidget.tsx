"use client";
import { useState, type FormEvent, type ReactNode } from "react";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatWidgetProps {
  isOpen: boolean;
  onToggle: () => void;
  messages: ChatMessage[];
  onSend: (question: string) => void;
  isLoading?: boolean;
  /** Slot livre para o app mostrar algo extra depois da última resposta —
   * ex. um link de WhatsApp quando o assistente sinaliza intenção de
   * compra. libs/web/ui não sabe o que é WhatsApp ou checkout. */
  footerNotice?: ReactNode;
}

/** Widget de chat no canto inferior — carregado via dynamic import pelo app
 * (para não pesar o carregamento inicial da página, ver
 * referencia-frontend-storefront.md, seção 1). Este componente é só a
 * casca visual; quem fala com o assistente de IA é o app chamador. */
export function ChatWidget({ isOpen, onToggle, messages, onSend, isLoading, footerNotice }: ChatWidgetProps) {
  const [draft, setDraft] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = draft.trim();
    if (!question) return;
    onSend(question);
    setDraft("");
  }

  return (
    <div className="chat-widget">
      {isOpen && (
        <div className="chat-widget__panel" role="dialog" aria-label="Assistente de compras">
          <div className="chat-widget__header">
            <h2>Assistente</h2>
            <button type="button" onClick={onToggle} aria-label="Fechar assistente">
              <span aria-hidden="true">✕</span>
            </button>
          </div>
          <div className="chat-widget__messages" aria-live="polite">
            {messages.length === 0 && (
              <p className="chat-widget__hint">Pergunte sobre tamanhos, cores ou o que temos disponível.</p>
            )}
            {messages.map((message, index) => (
              <p key={index} className={`chat-widget__message chat-widget__message--${message.role}`}>
                {message.content}
              </p>
            ))}
            {isLoading && (
              <p className="chat-widget__message chat-widget__message--assistant" aria-hidden="true">
                Digitando…
              </p>
            )}
          </div>
          {footerNotice && <div className="chat-widget__footer-notice">{footerNotice}</div>}
          <form className="chat-widget__form" onSubmit={handleSubmit}>
            <label htmlFor="chat-widget-input" className="sr-only">
              Sua pergunta
            </label>
            <input
              id="chat-widget-input"
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Digite sua pergunta"
            />
            <button type="submit" disabled={isLoading}>
              Enviar
            </button>
          </form>
        </div>
      )}
      <button
        type="button"
        className="chat-widget__toggle"
        aria-expanded={isOpen}
        onClick={onToggle}
        aria-label={isOpen ? "Fechar assistente de compras" : "Abrir assistente de compras"}
      >
        <span aria-hidden="true">{isOpen ? "✕" : "💬"}</span>
      </button>
    </div>
  );
}
