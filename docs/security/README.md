# Segurança

## Autenticação
Ver ADR-0003 — autenticação federada (Azure AD/MSAL, Google, extensível), sem senha própria armazenada.

## Segredos
Azure Key Vault, acessado via Managed Identity pelos serviços Azure sempre que possível.

## LGPD
Todo novo campo que armazene dado pessoal de cliente final ou da Nick precisa ser sinalizado no PR correspondente (ligação com base legal de tratamento). Um DPIA (avaliação de impacto) formal é um item pendente do roadmap de segurança, não bloqueante para o MVP, mas obrigatório antes de tratar volume relevante de dados de clientes.

## Alvo de longo prazo
ISO 27001 é o alvo, com reconhecimento explícito de que não será atendido por completo nesta fase. Prioridades atendidas desde já: sem senha própria em banco, gestão de segredos centralizada, RBAC granular (ver `identity`).
