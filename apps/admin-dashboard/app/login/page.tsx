"use client";

import { useState } from "react";
import { startLogin } from "@/lib/api";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin() {
    setLoading(true);
    setError(null);
    try {
      const redirectUri = `${window.location.origin}/callback`;
      const challenge = await startLogin(redirectUri);
      window.location.href = challenge.authorize_url;
    } catch {
      setError("Não foi possível iniciar o login. Tente novamente.");
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">Painel administrativo — Nick</h1>
      <p className="text-slate-600">Acesso restrito à equipe (papel staff ou admin).</p>
      <button
        onClick={handleLogin}
        disabled={loading}
        className="rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
      >
        {loading ? "Entrando..." : "Entrar"}
      </button>
      {error && <p className="text-red-600">{error}</p>}
    </main>
  );
}
