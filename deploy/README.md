# `deploy/` — como um app chega ao ambiente

Tudo o que leva o código para fora da máquina de quem desenvolve. Não é unidade: não tem
`unit.yaml`, não é importado por ninguém e pertence à plataforma no CODEOWNERS.

| Pasta | O que tem | Estado |
|---|---|---|
| [terraform/](terraform/README.md) | a infraestrutura do Azure: rede, Key Vault, Postgres, Container Apps, Azure OpenAI ([ADR-0004](../docs/kb/decisoes/0004-plataforma-de-execucao-azure.md)) | escrito, **nunca aplicado nem validado** |
| `observability/prometheus/` | a configuração de scrape do Prometheus | usado pelo `docker-compose.yml` |
| `observability/grafana/provisioning/` | a fonte de dados e o painel "Revold — Visão Geral", como código ([ADR-0017](../docs/kb/decisoes/0017-observabilidade-metricas-prometheus.md)) | usado pelo `docker-compose.yml` |

O `Dockerfile` de cada app **não** mora aqui: mora na pasta do app
(`apps/ecommerce/<app>/Dockerfile`), porque é parte do app e entra no fecho dele.

## Do release ao ambiente: o que existe

O modelo completo está em [docs/versionamento-e-deploy.md](../docs/versionamento-e-deploy.md). Em
resumo:

1. `uv run dev release <app> <parte>` prova o fecho e grava o BOM em `.releases/<app>.json`.
2. O PR entra na `main`; o `release.yml` confere o BOM, cria a tag `<app>@<versão>` e monta a
   imagem.
3. Com a variável de repositório `IMAGE_PUBLISH_ENABLED=true`, a imagem vai para o GitHub Container
   Registry, em `ghcr.io/<dono>/<repositório>/<app>:<versão>`.

## O que falta para existir um ambiente publicado

Decidido em 2026-11-15: a publicação da imagem (`IMAGE_PUBLISH_ENABLED`) fica desligada até este
ambiente existir. Os itens abaixo vêm antes.

Nada disto está feito. Cada item é trabalho com issue própria, e os três primeiros dependem de
credencial que o repositório não tem.

1. **Aplicar o Terraform.** Precisa de assinatura Azure, do state remoto e de `terraform validate`
   e `plan` revisados. O passo a passo inicial está em [terraform/README.md](terraform/README.md).
2. **Decidir o registro de imagem.** O `release.yml` sabe publicar no GHCR. O Container App pode
   puxar de lá, ou de um Azure Container Registry, que o Terraform ainda não cria.
3. **Trocar a imagem de exemplo.** O módulo `container-apps` aponta para uma imagem de exemplo, e só
   declara o `api-gateway`. Faltam o `event-worker` e a decisão sobre onde os sites são servidos.
4. **Aplicar migração no ambiente.** Hoje só existe `make migrate`, contra a pilha local. A ordem
   (migração antes ou depois da imagem nova) é respondida em cada PR de release
   ([CONTRIBUTING.md](../CONTRIBUTING.md), seção 8.2).
5. **Ambientes no GitHub** (*Settings -> Environments*): um de homologação e um de produção por
   app, com as credenciais dentro do ambiente e "Required reviewers" em produção. A regra: a mesma
   imagem nos dois; ambiente é promoção, não rebuild.

## Regras desta pasta

- **Segredo nunca entra aqui.** Variável do Terraform que é segredo vem de `TF_VAR_...` no ambiente
  de quem aplica, ou do Key Vault. Estado do Terraform (`*.tfstate`) está no `.gitignore`.
- **Mudança aqui afeta todas as unidades** no cálculo de afetados (`tooling/repo.yaml`): o CI roda
  tudo.
