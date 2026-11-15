# Política de segurança

O **revold** é o monorepo do produto de e-commerce e das bibliotecas que ele usa. Não há programa
público de recompensa por vulnerabilidade: o que segue vale para o time e para quem tiver acesso ao
repositório.

## Como reportar uma vulnerabilidade

**Não abra uma issue pública** para descrever uma falha de segurança ou um segredo exposto. Uma
issue é visível para todo mundo que enxerga o repositório, e descrever o problema em detalhe é o
mesmo que publicar o roteiro de exploração antes da correção.

Em vez disso:

1. Avise **em privado** um dos donos do repositório, `@SamuelSMatos` ou `@dmourans`.
2. Se o GitHub **Private vulnerability reporting** estiver habilitado, use a aba **Security >
   Report a vulnerability**: o relato fica restrito aos mantenedores.
3. Descreva o passo a passo de reprodução, o impacto e, se souber, uma sugestão de correção.

Trate o assunto como confidencial até que a correção esteja publicada na `main`.

## Segredos: a regra que o repositório inteiro segue

Segredo **nunca** vai para o git. Vale para código, teste, documentação e **nota de KB**. Nunca
comite nem registre:

- valor de variável de ambiente;
- credencial, senha, token ou chave;
- connection string;
- ID de recurso de nuvem;
- caminho absoluto de máquina;
- e-mail de pessoa.

Cite o **nome** da variável, nunca o valor. A referência de quais variáveis existem é o
**[.env.example](.env.example)**; o **`.env`** real fica só na sua máquina e nunca é versionado.
O desenho do ambiente publicado prevê os segredos no Azure Key Vault, lidos por identidade
gerenciada ([deploy/terraform/](deploy/terraform/README.md)), nunca no código. Esse ambiente ainda
não existe (CONTRIBUTING, seção 13).

As senhas que aparecem no `docker-compose.yml`, no `ci.yml` e no padrão de desenvolvimento do
`settings.py` dos apps (`revold_dev_only`, `revold_ci_only`) são de bancos descartáveis que só
existem na máquina de quem desenvolve ou no runner do CI. Não são segredo e nunca podem ser
reusadas num ambiente publicado.

## Dado pessoal (LGPD)

Todo campo novo que guarde dado pessoal de cliente final precisa ser sinalizado no PR
correspondente (seção "Arquitetura e segurança" do template). O detalhe está em
[docs/security/README.md](docs/security/README.md).

## O que o GitHub faz por você

O repositório usa o **secret scanning** com **push protection** do GitHub (ligado pelo dono com
`scripts/setup-rulesets.sh --apply`). O GitHub reconhece o formato dos tokens de centenas de
serviços (Azure, OpenAI, gateways de pagamento e afins) e **recusa o push** que traz um deles,
antes de o segredo chegar ao repositório. Se o seu push for recusado por isso:

- tire o segredo do arquivo **e do commit** da sua branch;
- se ele era real, considere-o vazado mesmo assim (ele já saiu da sua máquina) e siga
  [Se um segredo vazou](#se-um-segredo-vazou);
- o GitHub oferece um botão para liberar o push. **Nunca use para segredo de verdade.** Para um
  falso positivo (um valor de exemplo), explique no PR por que liberou.

## O que o CI já faz por você

O job **"Segurança"** do [CI](.github/workflows/ci.yml) roda em todo PR e inclui:

- **`bandit`**: análise estática de segurança do código Python. Achado de severidade média ou alta
  reprova.
- **`pip-audit`**: varredura de vulnerabilidades conhecidas nas dependências (informativo).
- Uma varredura textual que **falha o build** se o nome de uma credencial conhecida do projeto
  (token do gateway de pagamento, chave do LLM, senha do SMTP e afins) aparecer com valor no código.

Os workflows rodam com o menor privilégio necessário (`permissions: contents: read` por padrão).
Isso é uma rede de proteção, não uma licença para relaxar: a primeira linha de defesa é não escrever
o segredo. A varredura textual do CI é a segunda camada, atrás da do GitHub.

## Se um segredo vazou

Se um segredo foi comitado, mesmo que em um commit já sobrescrito:

1. **Considere-o comprometido e rotacione-o imediatamente** (troque a credencial ou o token na
   origem). Apagar o commit **não** basta: o histórico do git e os forks e clones podem reter o
   valor.
2. Avise os donos do repositório em privado.
3. Só depois trate a limpeza do histórico, se for o caso.

## Escopo suportado

A versão suportada é a que está na **`main`**. Correções de segurança seguem o fluxo normal do
projeto (branch a partir da `main`, PR para a `main`), com a prioridade que o risco exigir.
