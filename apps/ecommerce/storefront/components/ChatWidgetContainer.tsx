"use client";
import { useState } from "react";
import { ChatWidget, type ChatMessage } from "@revold/ui";
import { askAssistant } from "@/lib/api";
import { useUIStore } from "@/store/uiStore";

/** Liga a casca visual do ChatWidget ao core-ai-assistant (RAG via
 * /api/assistant/ask, já implementado no backend — ADR-0011). Quando o
 * assistente sinaliza intenção de compra (escalate_to_whatsapp), o
 * checkout de verdade continua sendo o carrinho (que já sabe montar o link
 * de WhatsApp) — este widget só oferece abrir o carrinho, não inventa um
 * link de WhatsApp por conta própria. */
export function ChatWidgetContainer() {
  const isOpen = useUIStore((state) => state.isChatOpen);
  const toggleChat = useUIStore((state) => state.toggleChat);
  const openCart = useUIStore((state) => state.openCart);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [escalate, setEscalate] = useState(false);

  async function handleSend(question: string) {
    const history = messages;
    setMessages((current) => [...current, { role: "user", content: question }]);
    setIsLoading(true);
    try {
      const reply = await askAssistant(question, history);
      setMessages((current) => [...current, { role: "assistant", content: reply.message }]);
      setEscalate(reply.escalate_to_whatsapp);
    } catch {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: "Não consegui responder agora — tente de novo em instantes." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <ChatWidget
      isOpen={isOpen}
      onToggle={toggleChat}
      messages={messages}
      onSend={handleSend}
      isLoading={isLoading}
      footerNotice={
        escalate ? (
          <button type="button" onClick={openCart}>
            Ver carrinho e falar com a Nick pelo WhatsApp
          </button>
        ) : undefined
      }
    />
  );
}
