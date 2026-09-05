# ADR-0008: CI/CD no GitHub Actions (não Azure DevOps)

**Status:** Aceito

## Contexto
O README original previa Azure DevOps Pipelines. O repositório, na prática, já está hospedado no GitHub (`github.com/SamuelSMatos/revold`). Rodar CI em uma plataforma diferente de onde o código vive adiciona um passo de integração (conectar Azure DevOps ao repositório GitHub) sem benefício claro nesta fase.

## Decisão
Usar GitHub Actions como pipeline de CI/CD, com os mesmos estágios descritos no README (quality gates → build → deploy staging → deploy production), adaptados para workflows do GitHub Actions (`.github/workflows/`). Deploy para Azure (Container Apps, ver ADR-0004) a partir do GitHub Actions via OIDC (sem segredo de longa duração armazenado no GitHub).

## Consequências
- Menos uma ferramenta para operar; o time de um só desenvolvedor não precisa alternar entre GitHub e Azure DevOps para ver o status de um PR.
- Se no futuro houver motivo real para Azure DevOps (ex.: exigência de um cliente/parceiro específico), a migração é isolada — os `Makefile` targets que os workflows chamam continuam os mesmos, só muda o arquivo de orquestração do CI.
