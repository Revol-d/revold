# `.releases/` — o BOM de cada release de app

Um arquivo por app Python: `<app>.json`. É gravado por `uv run dev release <app> <parte>` e entra
na `main` pelo PR de release. **Nunca edite à mão.**

Cada arquivo lista, para cada unidade do fecho do app, a distribuição, a versão e o sha256 do
`src/`, na ordem de instalação, mais o sha256 do `uv.lock`.

Dois usos:

- **O `release.yml`** confere o arquivo contra o código que entrou na `main` antes de criar a tag
  `<app>@<versão>`.
- **O gate de versão** do `uv run dev check` compara o `src/` de cada unidade com o arquivo: código
  que mudou com o mesmo número reprova.

Ainda não há nenhum release. Enquanto um app não tiver o arquivo dele aqui, o gate de versão não tem
com o que comparar e diz isso a cada rodada.

Detalhes: [docs/versionamento-e-deploy.md](../docs/versionamento-e-deploy.md) e a seção 8 do
[CONTRIBUTING.md](../CONTRIBUTING.md).
