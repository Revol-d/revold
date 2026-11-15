# ADR-0003: Autenticação federada, sem senha própria

**Status:** Aceito

## Contexto
O alvo de segurança de longo prazo é compliance ISO 27001, sabendo que não será atendido por completo no curto prazo. A prioridade concreta definida é: nunca armazenar senha de usuário em banco próprio, e não perder usuário por falta de uma opção de login conveniente.

## Decisão
`core-identity` não implementa cadastro/login com senha local. Autenticação é sempre delegada a provedores de identidade externos via OIDC/OAuth2:
- Microsoft Entra External ID / Azure AD B2C (via MSAL) como provedor principal, dado o ambiente Azure já decidido.
- Google como segundo provedor.
- Espaço para adicionar mais provedores (Apple, Facebook) conforme a base de clientes da Nick pedir, sem mudança estrutural — cada provedor é um adapter da mesma porta `IdentityProvider`.

`core-identity` mantém apenas: o mapeamento entre identidade federada → perfil interno, papéis (RBAC) e sessão. Nenhum hash de senha, nenhum fluxo de "esqueci minha senha" para manter.

Segredos de client (client id/secret de cada provedor, connection strings) ficam no Azure Key Vault. Serviços Azure acessam o Key Vault via Managed Identity sempre que possível, evitando distribuir a própria credencial do Key Vault.

## Consequências
- Superfície de ataque menor (sem senha própria para vazar ou sem rate limit de brute-force a implementar).
- Usuário depende de ter conta em algum provedor suportado — mitigado por oferecer mais de um provedor desde o início.
- Implementação local/dev não tem credencial real de Azure AD/Google ainda — ver adapter de desenvolvimento (`core-identity`, mock provider) como solução temporária, trocável por configuração quando as credenciais reais existirem.
