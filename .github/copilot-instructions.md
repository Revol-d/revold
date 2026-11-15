# Instruções do Copilot — revold

Guia **canônico** de agentes deste repositório: **[../AGENTS.md](../AGENTS.md)**. Leia e siga.

As regras abaixo são repetidas aqui para garantir que sejam vistas mesmo sem abrir o AGENTS.md:

1. **Nunca credite IA como co-autora** em commit, PR ou comentário. Proibido `Co-authored-by:` de
   qualquer ferramenta de IA (Copilot, Claude, GPT e afins). Co-autoria é só de pessoas reais.
2. **Nunca use emojis ou ícones** em mensagem de commit, título/descrição de PR ou comentário.
3. **Nunca commite nem dê push direto na `main`**: branch nova saindo da `main` sempre, e PR para
   a `main`.
4. **Não enfraqueça barreira para fazer passar** (`noqa`, `type: ignore`, `skip`, `|| true`) e não
   altere teste existente só para ele ficar verde.
5. **Rode os gates e cole a saída** antes de dizer que terminou: `uv run dev check` e
   `uv run dev test --affected -q`.

Divulgar **uso** de IA (na seção "Uso de IA" do PR) é permitido e esperado. Divulgar uso é
diferente de creditar autoria.

Convenções completas, fluxo de branch (trunk-based, PR para a `main`), KB e arquitetura:
**[../AGENTS.md](../AGENTS.md)**. O passo a passo: **[../CONTRIBUTING.md](../CONTRIBUTING.md)**.
