"""Bloqueia commit e push direto na branch protegida (`main`).

Regra do repositório (trunk-based, ADR-0028): nada entra na `main` por commit direto —
sempre uma branch nova (`feat/<nome>`, `fix/<nome>`, `chore/<nome>`, `docs/<nome>`) saindo
da `main` e PR para a `main`. Ver AGENTS.md e docs/branch-strategy.md.

Roda como hook de pre-commit e pre-push (ver .pre-commit-config.yaml).
Só usa a biblioteca padrão: precisa funcionar antes de qualquer `uv sync`.
"""

import os
import subprocess
import sys

PROTECTED = {"main"}


def _current_branch() -> str:
    """Nome da branch atual, ou string vazia em detached HEAD."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def main() -> int:
    """Retorna 1 (bloqueia) se a branch atual for a `main`, senão 0."""
    # Só para automação que precisa commitar na `main` de propósito (não existe nenhuma hoje).
    # Pessoa não usa isto: o ruleset do servidor recusaria o push de qualquer jeito.
    if os.environ.get("ALLOW_PROTECTED_BRANCH_COMMIT") == "1":
        return 0

    branch = _current_branch()
    if branch in PROTECTED:
        sys.stderr.write(
            f"\nBloqueado: '{branch}' e uma branch protegida — commit/push direto e proibido.\n"
            "Crie uma branch nova a partir da 'main' e leve a mudanca por PR para a 'main':\n\n"
            "    git switch -c feat/minha-mudanca origin/main\n\n"
            "Ver CONTRIBUTING.md, secao 4.2.\n\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
