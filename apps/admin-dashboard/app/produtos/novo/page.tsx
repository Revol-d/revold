"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  createCategory,
  createProduct,
  getCurrentUser,
  listCategories,
  type Category,
} from "@/lib/api";

const NOVA_CATEGORIA = "__nova__";

export default function NovoProdutoPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categorySlug, setCategorySlug] = useState("");
  const [newCategorySlug, setNewCategorySlug] = useState("");
  const [newCategoryName, setNewCategoryName] = useState("");
  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [priceAmount, setPriceAmount] = useState("");
  const [variantSize, setVariantSize] = useState("");
  const [variantColor, setVariantColor] = useState("");
  const [variantInStock, setVariantInStock] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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
        const cats = await listCategories();
        setCategories(cats);
        setCategorySlug(cats[0]?.slug ?? NOVA_CATEGORIA);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        setError("Não foi possível carregar as categorias.");
      } finally {
        setChecking(false);
      }
    }
    load();
  }, [router]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      let finalCategorySlug = categorySlug;
      if (categorySlug === NOVA_CATEGORIA) {
        if (!newCategorySlug || !newCategoryName) {
          setError("Preencha o slug e o nome da nova categoria.");
          setSubmitting(false);
          return;
        }
        const created = await createCategory(newCategorySlug, newCategoryName);
        finalCategorySlug = created.slug;
      }

      const variants =
        variantSize && variantColor
          ? [
              {
                sku: `${sku}-${variantSize}`.toUpperCase(),
                size: variantSize,
                color: variantColor,
                in_stock: variantInStock,
              },
            ]
          : [];

      const product = await createProduct({
        sku,
        name,
        categorySlug: finalCategorySlug,
        priceAmount,
        description,
        variants,
      });
      setSuccess(`Produto "${product.name}" (SKU ${product.sku}) criado.`);
      setSku("");
      setName("");
      setDescription("");
      setPriceAmount("");
      setVariantSize("");
      setVariantColor("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Já existe um produto com esse SKU.");
      } else if (err instanceof ApiError && err.status === 404) {
        setError("Categoria não encontrada.");
      } else {
        setError("Não foi possível criar o produto.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (checking) return <main className="p-6">Carregando...</main>;
  if (error && categories.length === 0 && !categorySlug) {
    return <main className="p-6 text-red-600">{error}</main>;
  }

  return (
    <main className="mx-auto max-w-xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Novo produto</h1>
        <a href="/estoque" className="text-sm underline">
          Voltar ao estoque
        </a>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">SKU</span>
          <input
            required
            value={sku}
            onChange={(e) => setSku(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2"
          />
        </label>

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
            <option value={NOVA_CATEGORIA}>+ nova categoria</option>
          </select>
        </label>

        {categorySlug === NOVA_CATEGORIA && (
          <div className="flex gap-4 rounded border border-dashed border-slate-300 p-3">
            <label className="flex flex-1 flex-col gap-1">
              <span className="text-sm font-medium">Slug da categoria</span>
              <input
                value={newCategorySlug}
                onChange={(e) => setNewCategorySlug(e.target.value)}
                placeholder="ex.: bolsas"
                className="rounded border border-slate-300 px-3 py-2"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1">
              <span className="text-sm font-medium">Nome da categoria</span>
              <input
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
                placeholder="ex.: Bolsas"
                className="rounded border border-slate-300 px-3 py-2"
              />
            </label>
          </div>
        )}

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Preço (BRL)</span>
          <input
            required
            value={priceAmount}
            onChange={(e) => setPriceAmount(e.target.value)}
            placeholder="ex.: 129.90"
            inputMode="decimal"
            className="rounded border border-slate-300 px-3 py-2"
          />
        </label>

        <fieldset className="rounded border border-slate-200 p-3">
          <legend className="px-1 text-sm font-medium">
            Primeira variante (opcional — mais variantes ficam para uma próxima versão)
          </legend>
          <div className="flex gap-4">
            <label className="flex flex-1 flex-col gap-1">
              <span className="text-sm">Tamanho</span>
              <input
                value={variantSize}
                onChange={(e) => setVariantSize(e.target.value)}
                placeholder="ex.: M"
                className="rounded border border-slate-300 px-3 py-2"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1">
              <span className="text-sm">Cor</span>
              <input
                value={variantColor}
                onChange={(e) => setVariantColor(e.target.value)}
                placeholder="ex.: Azul"
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
        </fieldset>

        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {submitting ? "Criando..." : "Criar produto"}
        </button>

        {error && <p className="text-red-600">{error}</p>}
        {success && <p className="text-green-700">{success}</p>}
      </form>
    </main>
  );
}
