# ADR-0001: Estratégia de Monorepo

**Status:** Aceito

## Contexto
A empresa nasce com um projeto piloto (e-commerce da Nick), mas o objetivo estratégico é que a base técnica sirva de framework reutilizável para projetos futuros. Não há prazo fixo para o piloto — o objetivo de curto prazo é entregar o site já na arquitetura desenhada; o de longo prazo é o repositório nascer novos projetos sem reescrita.

## Decisão
Adotar um monorepo único (`revold`) contendo contratos, cores de domínio, orchestrators, adapters, apps e infraestrutura como código, em vez de múltiplos repositórios por serviço.

Motivos:
- Um único ponto de verdade para os contratos (`contracts/`) compartilhados entre backend e frontend evita drift de versão entre repositórios.
- Refatorações que atravessam camadas (ex.: mudar uma porta e todos os adapters que a implementam) ficam atômicas em um único PR.
- Reuso entre projetos futuros é mais simples quando o histórico e as convenções já vivem no mesmo lugar.

## Consequências
- Precisa de disciplina de dependência entre pastas (ver ADR-0002) para não virar um "big ball of mud" só porque está no mesmo repositório.
- CI precisa ser capaz de rodar apenas os testes/build afetados pela mudança (path filtering), para não pagar o custo de build completo a cada PR pequeno.
- Ferramentas de workspace (`pnpm` para Node, `poetry` para Python) precisam ser configuradas desde o início — feito na configuração de tooling raiz.
