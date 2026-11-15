# ADR-0004: Plataforma de execução no Azure

**Status:** Aceito (revisável)

## Contexto
O ambiente de nuvem é Azure. O README original previa AKS + Terraform + Helm desde o primeiro projeto. Sem prazo fixo, a escolha entre isso e uma alternativa mais simples pode ser reavaliada — mas o princípio de IaC precisa estar aplicado corretamente desde o planejamento, para que provisionar recursos de nuvem não seja o gargalo do projeto.

## Decisão
Para este primeiro projeto, usar **Azure Container Apps** (não AKS) como plataforma de execução dos serviços (`api-gateway`, `workers`, futuros serviços por core), com:
- Azure Database for PostgreSQL – Flexible Server (gerenciado, sem operar cluster de banco).
- Azure Cache for Redis.
- Azure Key Vault para segredos, acessado via Managed Identity.
- Azure OpenAI para os modelos usados pelo `core-ai-assistant`.

Tudo declarado via Terraform desde o primeiro módulo (ver `iac/terraform/`), nunca criado manualmente pelo portal.

Kubernetes (AKS) fica como caminho de migração explícito, não descartado: se no futuro houver necessidade real de orquestração mais complexa (múltiplos serviços com escalonamento independente sofisticado, service mesh, etc.), a mesma disciplina de Terraform facilita a troca — o módulo de "plataforma de execução" é isolado dos demais (rede, banco, Key Vault não mudam).

## Consequências
- Menos operação (sem cluster Kubernetes para manter) e provisionamento mais rápido, o que atende diretamente o requisito de não demorar para ter recursos de nuvem disponíveis.
- Menos flexibilidade de orquestração do que AKS — aceitável, dado que não há ainda um cenário real que exija isso.
- `iac/kubernetes/` e Helm ficam como diretório reservado para quando (e se) a migração para AKS acontecer, não removidos do desenho.
