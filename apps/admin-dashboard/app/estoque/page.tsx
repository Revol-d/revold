"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  getCurrentUser,
  getStockLevel,
  listProducts,
  logout,
  receiveStock,
  type AuthenticatedUser,
  type Product,
  type StockLevel,
} from "@/lib/api";

interface Row {
  product: Product;
  stock: StockLevel | null;
}

export default function EstoquePage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
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

        const page = await listProducts();
        const withStock = await Promise.all(
          page.items.map(async (product): Promise<Row> => {
            try {
              const stock = await getStockLevel(product.sku);
              return { product, stock };
            } catch (err) {
              if (err instanceof ApiError && err.status === 404) {
                return { product, stock: null };
              }
              throw err;
            }
          })
        );
        setRows(withStock);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        setError("Não foi possível carregar o estoque.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  async function handleReceive(sku: string) {
    const raw = window.prompt(`Quantidade a repor para ${sku}:`, "10");
    if (!raw) return;
    const quantity = Number(raw);
    if (!Number.isInteger(quantity) || quantity <= 0) {
      window.alert("Quantidade inválida.");
      return;
    }
    setPending(sku);
    try {
      const stock = await receiveStock(sku, quantity);
      setRows((prev) => prev.map((row) => (row.product.sku === sku ? { ...row, stock } : row)));
    } catch {
      window.alert("Não foi possível repor o estoque.");
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
    <main className="mx-auto max-w-4xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Estoque</h1>
          {user && (
            <p className="text-sm text-slate-600">
              {user.name} · {user.roles.join(", ")}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <a href="/produtos/novo" className="text-sm underline">
            Novo produto
          </a>
          <button onClick={handleLogout} className="text-sm underline">
            Sair
          </button>
        </div>
      </header>
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-slate-300">
            <th className="py-2">SKU</th>
            <th className="py-2">Produto</th>
            <th className="py-2">Em estoque</th>
            <th className="py-2">Reservado</th>
            <th className="py-2">Disponível</th>
            <th className="py-2" />
          </tr>
        </thead>
        <tbody>
          {rows.map(({ product, stock }) => (
            <tr key={product.sku} className="border-b border-slate-100">
              <td className="py-2">{product.sku}</td>
              <td className="py-2">{product.name}</td>
              <td className="py-2">{stock?.quantity_on_hand ?? "—"}</td>
              <td className="py-2">{stock?.quantity_reserved ?? "—"}</td>
              <td className="py-2">{stock?.quantity_available ?? "—"}</td>
              <td className="py-2">
                <button
                  onClick={() => handleReceive(product.sku)}
                  disabled={pending === product.sku}
                  className="rounded bg-slate-900 px-2 py-1 text-xs text-white disabled:opacity-50"
                >
                  {pending === product.sku ? "Repondo..." : "Repor estoque"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
