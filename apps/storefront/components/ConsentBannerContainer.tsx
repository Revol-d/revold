"use client";
import { useEffect, useState } from "react";
import { ConsentBanner } from "@revold/ui";

const STORAGE_KEY = "revold_cookie_consent";

export function ConsentBannerContainer() {
  const [decision, setDecision] = useState<"unset" | "all" | "essential-only">("unset");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "all" || stored === "essential-only") setDecision(stored);
    } catch {
      // localStorage indisponível — banner some visível até a próxima visita
    }
  }, []);

  function persist(value: "all" | "essential-only") {
    setDecision(value);
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch {
      // segue só nesta sessão
    }
  }

  return (
    <ConsentBanner
      isVisible={decision === "unset"}
      onAcceptAll={() => persist("all")}
      onRejectNonEssential={() => persist("essential-only")}
    />
  );
}
