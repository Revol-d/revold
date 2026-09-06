import { create } from "zustand";

/** Estado de UI efêmero (não persistido, não vem do servidor) — drawer do
 * carrinho aberto/fechado, widget de chat aberto/fechado. Dados remotos
 * (catálogo, carrinho) ficam com o TanStack Query; isto aqui é só o README
 * do monorepo aplicado (Zustand para estado de UI, ver
 * referencia-frontend-storefront.md, seção 2). */
interface UIState {
  isCartOpen: boolean;
  openCart: () => void;
  closeCart: () => void;

  isChatOpen: boolean;
  toggleChat: () => void;
  closeChat: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isCartOpen: false,
  openCart: () => set({ isCartOpen: true }),
  closeCart: () => set({ isCartOpen: false }),

  isChatOpen: false,
  toggleChat: () => set((state) => ({ isChatOpen: !state.isChatOpen })),
  closeChat: () => set({ isChatOpen: false }),
}));
