# ADR-0002: Separação em Cores (Bounded Contexts)

**Status:** Aceito

## Contexto
O domínio do e-commerce da Nick tem responsabilidades bem distintas (identidade, catálogo, carrinho, estoque, comunicação externa, assistente de IA, notificações). Misturá-las em um monólito de domínio único dificultaria testabilidade e a reutilização em projetos futuros que não precisem de todas as partes.

## Decisão
Separar o domínio em sete cores independentes sob `cores/`, cada um um bounded context de DDD com sua própria linguagem ubíqua: `core-identity`, `core-catalog`, `core-cart`, `core-inventory`, `core-communication`, `core-ai-assistant`, `core-notification`.

Regras:
- Um core nunca importa código de dentro de outro core diretamente — comunicação entre cores acontece via eventos (`contracts/events/`) ou através de um orchestrator.
- Um core define portas (interfaces) para tudo que é infraestrutura (banco, fila, serviço externo); implementações ficam em `adapters/`.
- Um core não depende de framework web/ORM — essas dependências ficam isoladas nos adapters e nos orchestrators/apps que os compõem.

## Consequências
- Mais arquivos/módulos do que um monólito simples, mas cada core pode evoluir, ser testado e (no limite) ser extraído para um serviço próprio sem reescrever regra de negócio.
- Exige que todo novo core comece pelo contrato (ver ADR de Contract-First implícito no README) antes da implementação.
- O primeiro core a ser implementado por completo, como prova de conceito da arquitetura, é o `core-catalog` (não depende de credenciais externas ainda não disponíveis, ao contrário de identity/communication).
