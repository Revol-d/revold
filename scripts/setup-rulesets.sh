#!/usr/bin/env bash
# Aplica os rulesets do fluxo trunk-based (ADR-0028).
#
# Pre-requisitos:
#   - GitHub CLI ('gh') instalada e autenticada ('gh auth login'), com conta ADMIN do repo.
#   - Rodar dentro do clone do repositorio, com o remoto 'origin' apontando para o GitHub.
#
# Uso:
#   scripts/setup-rulesets.sh            # so MOSTRA o que faria (padrao, nao muda nada)
#   scripts/setup-rulesets.sh --apply    # aplica de verdade
#
# O que faz, em ordem:
#   1. Merge do repositorio: so squash, apaga a branch depois do merge.
#   2. Ruleset "main" (branch padrao):
#        - exige PR e o check agregado `CI OK` (job `ci-ok` do ci.yml);
#        - exige revisao de CODEOWNERS (1 aprovacao de qualquer dono basta);
#        - descarta aprovacao quando entra push novo;
#        - exige aprovacao do ultimo push (quem empurrou por ultimo nao se aprova);
#        - so squash merge, historico linear;
#        - bloqueia force-push e delecao.
#   3. Ruleset "tags-de-release" (`*@*`, ex.: `api-gateway@0.2.0`): so o GitHub Actions
#      cria, move ou apaga essas tags. Quem publica e o workflow de release.
#   4. Secret scanning e push protection do GitHub: o GitHub reconhece o formato dos tokens de
#      centenas de servicos e RECUSA o push que traz um deles. Em repositorio publico e gratis.
#      E a primeira camada contra segredo commitado; a busca por nome do ci.yml e a segunda
#      (CONTRIBUTING, secao 13, item 5).
#
# Cada ruleset e procurado pelo nome: se existe, e atualizado (PUT); se nao, e criado (POST).
# Seguro rodar mais de uma vez.
#
# O que este script NAO faz (de proposito):
#   - Nao apaga a branch `develop`, se ela existir no remoto. O CI antigo escutava `develop`;
#     o fluxo novo nao tem essa branch (docs/branch-strategy.md).
#   - Nao remove protecao classica antiga da `main`, se houver. Ela soma com o ruleset (vale a
#     regra mais restritiva das duas), entao convive sem abrir buraco. Remover depois de
#     conferir o ruleset funcionando:
#       gh api --method DELETE repos/<owner>/<repo>/branches/main/protection
#
# O id 15368 abaixo e o app "GitHub Actions". E o ator que pode furar o ruleset de tags,
# para o workflow de release criar a tag com o GITHUB_TOKEN. Conferir em:
#   gh api /apps/github-actions --jq .id

set -euo pipefail

apply=0
case "${1:-}" in
  --apply) apply=1 ;;
  "") ;;
  *) echo "Uso: $0 [--apply]"; exit 2 ;;
esac

command -v gh >/dev/null 2>&1 || { echo "GitHub CLI ('gh') nao encontrada. Instale e rode 'gh auth login' antes de continuar."; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "GitHub CLI nao autenticada. Rode 'gh auth login'."; exit 1; }

repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
echo "Repositorio: $repo"
[ "$apply" -eq 1 ] || echo "Modo de conferencia: nada sera alterado. Use --apply para aplicar."

read -r -d '' RULESET_MAIN <<'JSON' || true
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "require_code_owner_review": true,
        "dismiss_stale_reviews_on_push": true,
        "require_last_push_approval": true,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [{ "context": "CI OK" }]
      }
    }
  ]
}
JSON

read -r -d '' RULESET_TAGS <<'JSON' || true
{
  "name": "tags-de-release",
  "target": "tag",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["refs/tags/*@*"], "exclude": [] } },
  "bypass_actors": [
    { "actor_id": 15368, "actor_type": "Integration", "bypass_mode": "always" }
  ],
  "rules": [
    { "type": "creation" },
    { "type": "update" },
    { "type": "deletion" }
  ]
}
JSON

aplicar_ruleset() {
  local nome="$1" corpo="$2" id
  id="$(gh api "repos/$repo/rulesets" --jq ".[] | select(.name == \"$nome\") | .id" || true)"
  if [ "$apply" -eq 0 ]; then
    if [ -n "$id" ]; then echo "-- atualizaria o ruleset '$nome' (id $id):"; else echo "-- criaria o ruleset '$nome':"; fi
    echo "$corpo"
    return
  fi
  if [ -n "$id" ]; then
    echo "Atualizando o ruleset '$nome' (id $id)..."
    echo "$corpo" | gh api --method PUT "repos/$repo/rulesets/$id" --input - >/dev/null
  else
    echo "Criando o ruleset '$nome'..."
    echo "$corpo" | gh api --method POST "repos/$repo/rulesets" --input - >/dev/null
  fi
}

# --- 1. metodo de merge ----------------------------------------------------------
if [ "$apply" -eq 1 ]; then
  echo "Configurando merge: so squash, apaga a branch depois do merge..."
  gh repo edit "$repo" --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --delete-branch-on-merge
else
  echo "-- configuraria o merge: so squash, apaga a branch depois do merge"
fi

# --- 2 e 3. rulesets ---------------------------------------------------------------
aplicar_ruleset "main" "$RULESET_MAIN"
aplicar_ruleset "tags-de-release" "$RULESET_TAGS"

# --- 4. secret scanning e push protection -------------------------------------------
# Por ultimo e sem derrubar o script: se a conta ou o plano nao permitir, os rulesets ja
# foram aplicados, e o aviso diz o que ligar na mao (Settings -> Code security).
if [ "$apply" -eq 1 ]; then
  echo "Ligando secret scanning e push protection..."
  gh api --method PATCH "repos/$repo" \
    -f 'security_and_analysis[secret_scanning][status]=enabled' \
    -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled' >/dev/null \
    || echo "AVISO: nao consegui ligar pela API. Ligue em Settings -> Code security: 'Secret scanning' e 'Push protection'."
else
  echo "-- ligaria secret scanning e push protection. Estado atual (so administrador enxerga):"
  gh api "repos/$repo" --jq '.security_and_analysis // "(nao visivel para esta conta)"' || true
fi

if [ "$apply" -eq 1 ]; then
  echo "Rulesets do repositorio agora:"
  gh api "repos/$repo/rulesets" --jq '.[].name'
  echo "Seguranca do repositorio agora:"
  gh api "repos/$repo" --jq '.security_and_analysis' || true
  echo "Conferir: abrir um PR de teste para a 'main' e ver o 'CI OK' obrigatorio e a revisao pedida aos donos."
fi
