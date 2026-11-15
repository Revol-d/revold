"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { completeLogin } from "@/lib/api";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    if (!code || !state) {
      setError("Callback inválido: faltam code/state.");
      return;
    }
    completeLogin(code, state)
      .then(() => router.replace("/estoque"))
      .catch(() => setError("Não foi possível concluir o login."));
  }, [searchParams, router]);

  if (error) {
    return (
      <>
        <p className="text-red-600">{error}</p>
        <a href="/login" className="underline">
          Tentar novamente
        </a>
      </>
    );
  }

  return <p>Entrando...</p>;
}

export default function CallbackPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
      <Suspense fallback={<p>Entrando...</p>}>
        <CallbackContent />
      </Suspense>
    </main>
  );
}
