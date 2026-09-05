"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ApiError,
  addProductVariant,
  getCurrentUser,
  getProduct,
  listCategories,
  updateProduct,
  type Category,
  type Product,
} from "@/lib/api";

export default function EditarProdutoPage() {
  const router = useRouter();
  const params = useParams<{ sku: string }>();
  const sku = decodeURIComponent(params.sku);

  const [checking, setChecking] = useState(true);
  const [product, setProduct] = useState<Product | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [categorySlug, setCategorySlug] = useState("");
  const [priceAmount, setPriceAmount] = useState("");
  const [description, setDescription] = useState("");
  const [savingProduct, setSavingProduct] = useState(false);
  const [productSuccess, setProductSuccess] = useState<string | null>(null);
  const [productError, setProductError] = useState<string | null>(null);

  const [variantSku, setVariantSku] = useState("");
  const [variantSize, setVariantSize] = useState("");
  const [variantColor, setVariantColor] = useState("");
  const [variantInStock, setVariantInStock] = useState(true);
  const [savingVariant, setSavingVariant] = useState(false);
  const [variantError, setVariantError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const me = await getCurrentUser();
        const isStaff = me.roles.includes("staff") || me.roles.includes("admin");
        if (!isStaff) {
          setError("Sua conta não tem papel STAFF/ADMIN — fale com a Nick para liberar acesso.");
          setChecking(false);
          return;
        }
        const [prod, cats] = await Promise.all([getProduct(sku), listCategories()]);
        setProduct(prod);
        setCategories(cats);
        setName(prod.name);
        setCategorySlug(prod.category.slug);
        setPriceAmount(prod.price.amount);
        setDescription(prod.description);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        if (err instanceof ApiError && err.status === 404) {
          setError(`Produto ${sku} não encontrado.`);
        } else {
          setError("Não foi possível carregar o produto.");
        }
      } finally {
        setChecking(false);
      }
    }
    load();
  }, [router, sku]);

  async function handleSaveProduct(event: React.FormEvent) {
    event.preventDefault();
    setProductError(null);
    setProductSuccess(null);
    setSavingProduct(true);
    try {
      const updated = await updateProduct(sku, {
        name,
        categorySlug,
        priceAmount,
        description,
      });
      setProduct(updated);
      setProductSuccess("Produto atualizado.");
    } catch {
      setProductError("Não foi possível salvar as alterações.");
    } finally {
      setSavingProduct(false);
    }
  }

  async function handleAddVariant(event: React.FormEvent) {
    event.preventDefault();
    setVariantError(null);
    setSavingVariant(true);
    try {
      const updated = await addProductVariant(sku, {
        sku: variantSku,
        size: variantSize,
        color: variantColor,
        in_stock: variantInStock,
      });
      setProduct(updated);
      setVariantSku("");
      setVariantSize("");
      setVariantColor("");
      setVariantInStock(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setVariantError("Já existe uma variante com esse SKU neste produto.");
      } else {
        setVariantError("Não foi possível adicionar a variante.");
      }
    } finally {
      setSavingVariant(false);
    }
  }

  if (checking) return <main className="p-6">Carregando...</main>;
  if (error) return <main className="p-6 text-red-600">{error}</main>;
  if (!product) return null;

  return (
    <main className="mx-auto max-w-xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Editar produto</h1>
        <a href="/estoque" className="text-sm underline">
          Voltar ao estoque
        </a>
      </div>

      <form onSubmit={handleSaveProduct} className="flex flex-col gap-4">
        <p className="text-sm text-slate-600">SKU: {product.sku} (não pode ser alterado)</p>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Nome</span>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Descrição</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2"
            rows={3}
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Categoria</span>
          <select
            value={categorySlug}
            onChange={(e) => setCategorySlug(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2"
          >
            {categories.map((category) => (
              <option key={category.slug} value={category.slug}>
                {category.name}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Preço (BRL)</span>
          <input
            required
            value={priceAmount}
            onChange={(e) => setPriceAmount(e.target.value)}
            inputMode="decimal"
            className="rounded border border-slate-300 px-3 py-2"
          />
        </label>

        <button
          type="submit"
          disabled={savingProduct}
          className="rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {savingProduct ? "Salvando..." : "Salvar alterações"}
        </button>

        {productError && <p className="text-red-600">{productError}</p>}
        {productSuccess && <p className="text-green-700">{productSuccess}</p>}
      </form>

      <hr className="my-8 border-slate-200" />

      <h2 className="mb-3 text-lg font-semibold">Variantes</h2>
      <ul className="mb-4 flex flex-col gap-1 text-sm">
        {product.variants.map((variant) => (
          <li key={variant.sku} className="flex justify-between rounded border border-slate-100 px-3 py-1.5">
            <span>
              {variant.sku} — {variant.size} / {variant.color}
            </span>
            <span className={variant.in_stock ? "text-green-700" : "text-slate-400"}>
              {variant.in_stock ? "em estoque" : "sem estoque"}
            </span>
          </li>
        ))}
        {product.variants.length === 0 && (
          <li className="text-slate-500">Nenhuma variante cadastrada ainda.</li>
        )}
      </ul>

      <form onSubmit={handleAddVariant} className="flex flex-col gap-3 rounded border border-dashed border-slate-300 p-3">
        <span className="text-sm font-medium">Adicionar variante</span>
        <div className="flex gap-3">
          <label className="flex flex-1 flex-col gap-1">
            <span className="text-sm">SKU da variante</span>
            <input
              required
              value={variantSku}
              onChange={(e) => setVariantSku(e.target.value)}
              placeholder={`ex.: ${product.sku}-GG`}
              className="rounded border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="flex flex-1 flex-col gap-1">
            <span className="text-sm">Tamanho</span>
            <input
              required
              value={variantSize}
              onChange={(e) => setVariantSize(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2"
            />
          </label>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex flex-1 flex-col gap-1">
            <span className="text-sm">Cor</span>
            <input
              required
              value={variantColor}
              onChange={(e) => setVariantColor(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="flex items-center gap-2 self-end pb-2">
            <input
              type="checkbox"
              checked={variantInStock}
              onChange={(e) => setVariantInStock(e.target.checked)}
            />
            <span className="text-sm">Em estoque</span>
          </label>
        </div>
        <button
          type="submit"
          disabled={savingVariant}
          className="self-start rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {savingVariant ? "Adicionando..." : "Adicionar variante"}
        </button>
        {variantError && <p className="text-red-600">{variantError}</p>}
      </form>
    </main>
  );
}
