"use client";
import { useRef } from "react";

export interface SizeOption {
  value: string;
  label: string;
  available: boolean;
}

export interface SizeSelectorProps {
  options: SizeOption[];
  selected?: string;
  onSelect: (value: string) => void;
}

/** Grade de tamanho navegável por setas (roving tabindex) — só o item
 * selecionado (ou o primeiro) fica no fluxo do Tab; ←/→ movem entre os
 * itens. Indisponibilidade via `aria-disabled` + texto, não só cor/opacidade
 * (ver referencia-frontend-storefront.md, seção 3). */
export function SizeSelector({ options, selected, onSelect }: SizeSelectorProps) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  function handleKeyDown(event: React.KeyboardEvent, index: number) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const delta = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (index + delta + options.length) % options.length;
    refs.current[nextIndex]?.focus();
  }

  const selectedIndex = Math.max(
    0,
    options.findIndex((o) => o.value === selected),
  );

  return (
    <div className="size-selector" role="group" aria-label="Tamanho">
      {options.map((option, index) => (
        <button
          key={option.value}
          ref={(el) => {
            refs.current[index] = el;
          }}
          type="button"
          className="size-selector__option"
          tabIndex={index === selectedIndex ? 0 : -1}
          aria-pressed={option.value === selected}
          aria-disabled={!option.available}
          disabled={!option.available}
          onKeyDown={(e) => handleKeyDown(e, index)}
          onClick={() => option.available && onSelect(option.value)}
        >
          {option.label}
          {!option.available && <span className="sr-only"> (indisponível)</span>}
        </button>
      ))}
    </div>
  );
}
