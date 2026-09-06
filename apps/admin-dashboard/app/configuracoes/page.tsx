"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  getCurrentUser,
  getStoreSettings,
  updateStoreSettings,
  type StoreSettings,
} from "@/lib/api";

export default function ConfiguracoesPage() {
  const router = useRouter();

  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [cnpj, setCnpj] = useState("");
  const [storeName, setStoreName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [storeAddress, setStoreAddress] = useState("");
  const [lowStockThreshold, setLowStockThreshold] = useState("5");

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  function applySettings(settings: StoreSettings) {
    setCnpj(settings.cnpj);
    setStoreName(settings.store_name);
    setContactEmail(settings.contact_email);
    setContactPhone(settings.contact_phone);
    setStoreAddress(settings.store_address);
    setLowStockThreshold(String(settings.low_stock_threshold));
  }

  useEffect(() => {
    async function load() {
      try {
        const me = await getCurrentUser();
        if (!me.roles.includes("admin")) {
          setError("Sua conta não tem papel ADMIN — só a Nick pode editar estas configurações.");
          setChecking(false);
          return;
        }
        const settings = await getStoreSettings();
        applySettings(settings);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        setError("Não foi possível carregar as configurações da loja.");
      } finally {
        setChecking(false);
      }
    }
    load();
  }, [router]);

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    setSaveError(null);
    setSuccess(null);
    setSaving(true);
    try {
      const parsedThreshold = Number.parseInt(lowStockThreshold, 10);
      const updated = await updateStoreSettings({
        cnpj,
        store_name: storeName,
        contact_email: contactEmail,
        contact_phone: contactPhone,
        store_address: storeAddress,
        low_stock_threshold: Number.isNaN(parsedThreshold) ? undefined : parsedThreshold,
      });
      applySettings(updated);
      setSuccess("Configurações salvas.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setSaveError("Confira o CNPJ e o e-mail de contato — algum deles não é válido.");
      } else {
        setSaveError("Não foi possível salvar as configurações.");
      }
    } finally {
      setSaving(false);
    }
  }

  if (checking) return <main className="p-6">Carregando...</main>;
  if (error) return <main className="p-6 text-red-600">{error}</main>;

  return (
    <main className="mx-auto max-w-xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Configurações da loja</h1>
        <a href="/estoque" className="text-sm underline">
          Voltar ao estoque
        </a>
      </div>

      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <fieldset className="flex flex-col gap-4 rounded border border-slate-200 p-4">
          <legend className="px-1 text-sm font-medium text-slate-700">Dados da loja</legend>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">CNPJ</span>
            <input
              value={cnpj}
              onChange={(e) => setCnpj(e.target.value)}
              placeholder="00.000.000/0000-00"
              className="rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">Nome da loja</span>
            <input
              value={storeName}
              onChange={(e) => setStoreName(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">Endereço</span>
            <input
              value={storeAddress}
              onChange={(e) => setStoreAddress(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2"
            />
          </label>
        </fieldset>

        <fieldset className="flex flex-col gap-4 rounded border border-slate-200 p-4">
          <legend className="px-1 text-sm font-medium text-slate-700">Contato</legend>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">E-mail de contato</span>
            <input
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">Telefone de contato</span>
            <input
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2"
            />
          </label>
        </fieldset>

        <fieldset className="flex flex-col gap-4 rounded border border-slate-200 p-4">
          <legend className="px-1 text-sm font-medium text-slate-700">Configurações gerais</legend>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">Limiar de estoque baixo</span>
            <input
              inputMode="numeric"
              value={lowStockThreshold}
              onChange={(e) => setLowStockThreshold(e.target.value)}
              className="w-32 rounded border border-slate-300 px-3 py-2"
            />
            <span className="text-xs text-slate-500">
              Abaixo dessa quantidade disponível, um aviso de estoque baixo é disparado. Vale a
              partir de agora, sem precisar de novo deploy.
            </span>
          </label>
        </fieldset>

        <button
          type="submit"
          disabled={saving}
          className="self-start rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {saving ? "Salvando..." : "Salvar configurações"}
        </button>

        {saveError && <p className="text-red-600">{saveError}</p>}
        {success && <p className="text-green-700">{success}</p>}
      </form>
    </main>
  );
}
