"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  cancelOrder,
  getCurrentUser,
  listOrders,
  logout,
  markOrderDelivered,
  markOrderPaid,
  markOrderShipped,
  type AuthenticatedUser,
  type Order,
} from "@/lib/api";

const PAYMENT_LABEL: Record<Order["payment_status"], string> = {
  pending: "Aguardando confirmação",
  paid: "Pago",
  cancelled: "Cancelado",
};

const FULFILLMENT_LABEL: Record<Order["fulfillment_status"], string> = {
  pending: "Aguardando envio",
  shipped: "Enviado",
  delivered: "Entregue",
};

export default function PedidosPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  async function load() {
    try {
      const me = await getCurrentUser();
      setUser(me);
      const isStaff = me.roles.includes("staff") || me.roles.includes("admin");
      if (!isStaff) {
        setError("Sua conta não tem papel STAFF/ADMIN — fale com a Nick para liberar acesso.");
        setLoading(false);
        return;
      }
      const page = await listOrders();
      setOrders(page.items);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.replace("/login");
        return;
      }
      setError("Não foi possível carregar os pedidos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  async function withPending(orderId: string, action: () => Promise<Order>) {
    setPending(orderId);
    try {
      const updated = await action();
      setOrders((prev) => prev.map((o) => (o.order_id === orderId ? updated : o)));
    } catch {
      window.alert("Não foi possível atualizar este pedido.");
    } finally {
      setPending(null);
    }
  }

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  if (loading) return <main className="p-6">Carregando...</main>;
  if (error) return <main className="p-6 text-red-600">{error}</main>;

  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Pedidos</h1>
          {user && (
            <p className="text-sm text-slate-600">
              {user.name} · {user.roles.join(", ")}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <a href="/estoque" className="text-sm underline">
            Estoque
          </a>
          <button onClick={handleLogout} className="text-sm underline">
            Sair
          </button>
        </div>
      </header>

      {orders.length === 0 ? (
        <p className="text-sm text-slate-600">Nenhum pedido ainda — aparece aqui assim que o primeiro carrinho fechar checkout.</p>
      ) : (
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-slate-300">
              <th className="py-2">Pedido</th>
              <th className="py-2">Itens</th>
              <th className="py-2">Total</th>
              <th className="py-2">Pagamento</th>
              <th className="py-2">Entrega</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.order_id} className="border-b border-slate-100 align-top">
                <td className="py-2 font-mono text-xs">{order.order_id.slice(0, 8)}</td>
                <td className="py-2">
                  {order.lines.map((line) => (
                    <div key={line.sku}>
                      {line.quantity}x {line.product_name} ({line.variant_label})
                    </div>
                  ))}
                </td>
                <td className="py-2">
                  {order.total} {order.currency}
                </td>
                <td className="py-2">{PAYMENT_LABEL[order.payment_status]}</td>
                <td className="py-2">{FULFILLMENT_LABEL[order.fulfillment_status]}</td>
                <td className="py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    {order.payment_status === "pending" && (
                      <>
                        <button
                          onClick={() => withPending(order.order_id, () => markOrderPaid(order.order_id))}
                          disabled={pending === order.order_id}
                          className="rounded bg-slate-900 px-2 py-1 text-xs text-white disabled:opacity-50"
                        >
                          Marcar pago
                        </button>
                        <button
                          onClick={() => withPending(order.order_id, () => cancelOrder(order.order_id))}
                          disabled={pending === order.order_id}
                          className="text-xs text-red-600 underline disabled:opacity-50"
                        >
                          Cancelar
                        </button>
                      </>
                    )}
                    {order.payment_status === "paid" && order.fulfillment_status === "pending" && (
                      <button
                        onClick={() => withPending(order.order_id, () => markOrderShipped(order.order_id))}
                        disabled={pending === order.order_id}
                        className="rounded bg-slate-900 px-2 py-1 text-xs text-white disabled:opacity-50"
                      >
                        Marcar enviado
                      </button>
                    )}
                    {order.fulfillment_status === "shipped" && (
                      <button
                        onClick={() => withPending(order.order_id, () => markOrderDelivered(order.order_id))}
                        disabled={pending === order.order_id}
                        className="rounded bg-slate-900 px-2 py-1 text-xs text-white disabled:opacity-50"
                      >
                        Marcar entregue
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
