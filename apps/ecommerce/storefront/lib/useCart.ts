"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addCartItem,
  getCart,
  removeCartItem,
  startCheckout,
  updateCartItemQuantity,
  type CartDTO,
} from "@/lib/api";
import { getOrCreateCartId } from "@/lib/cart-id";

const CART_QUERY_KEY = ["cart"] as const;

/** Um único hook para tudo que precisa do carrinho — SiteHeader (contador),
 * CartDrawer (lista completa) e AddToCartButton (mutação de adicionar) todos
 * usam esta mesma chave de query, então uma mutação em qualquer um invalida
 * e atualiza os outros automaticamente. cart_id só existe no navegador
 * (localStorage), por isso a query fica desabilitada até o primeiro efeito
 * rodar (evita divergência de hidratação SSR/CSR). */
export function useCart() {
  const [cartId, setCartId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    setCartId(getOrCreateCartId());
  }, []);

  const cartQuery = useQuery<CartDTO>({
    queryKey: [...CART_QUERY_KEY, cartId],
    queryFn: () => getCart(cartId as string),
    enabled: cartId !== null,
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: CART_QUERY_KEY });
  }

  const addItemMutation = useMutation({
    mutationFn: (item: { sku: string; name: string; variant_label: string; unit_price: string; quantity?: number }) =>
      addCartItem(cartId as string, item),
    onSuccess: (data) => queryClient.setQueryData([...CART_QUERY_KEY, cartId], data),
  });

  const updateQuantityMutation = useMutation({
    mutationFn: ({ sku, quantity }: { sku: string; quantity: number }) =>
      updateCartItemQuantity(cartId as string, sku, quantity),
    onSuccess: (data) => queryClient.setQueryData([...CART_QUERY_KEY, cartId], data),
  });

  const removeItemMutation = useMutation({
    mutationFn: (sku: string) => removeCartItem(cartId as string, sku),
    onSuccess: (data) => queryClient.setQueryData([...CART_QUERY_KEY, cartId], data),
  });

  const checkoutMutation = useMutation({
    mutationFn: () => startCheckout(cartId as string),
    onSuccess: () => invalidate(),
  });

  const items = cartQuery.data?.items ?? [];
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0);

  return {
    cartId,
    cart: cartQuery.data,
    items,
    itemCount,
    isLoading: cartQuery.isLoading,
    addItem: addItemMutation.mutateAsync,
    isAdding: addItemMutation.isPending,
    updateQuantity: (sku: string, quantity: number) => updateQuantityMutation.mutate({ sku, quantity }),
    removeItem: (sku: string) => removeItemMutation.mutate(sku),
    checkout: checkoutMutation.mutateAsync,
    isCheckingOut: checkoutMutation.isPending,
    checkoutError: checkoutMutation.error instanceof Error ? checkoutMutation.error.message : undefined,
  };
}
