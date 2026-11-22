# Imagem do SQL Server para dev local (docker-compose) e CI -- mesma usada em
# .github/workflows/ci.yml (job `tests`). Dois achados reais que a imagem oficial
# sozinha não resolve (ver o plano de migração Postgres -> Azure SQL, docs internos):
#
# 1. SQL Server 2025 (17.x), não 2022: o tipo nativo VECTOR só existe a partir desta
#    versão do motor -- confirmado rodando a migração contra 2022-latest ("Cannot
#    find data type VECTOR", erro 2715).
# 2. Full-Text Search não vem instalado -- "Full-Text Search is not installed"
#    (erro 7609) ao criar o catálogo da busca do catalog. Instalar via `docker exec`
#    num container já rodando NÃO funciona (só surte efeito antes do primeiro start
#    do sqlservr); e o pacote mora no repositório específico do produto
#    (mssql-server-2025, Ubuntu 24.04/noble -- confirmado via @@VERSION dentro da
#    própria imagem), não no repositório "prod" que a imagem já traz.
#
# O entrypoint também cria o banco `revold` sozinho no primeiro start (a imagem
# oficial só cria o `master`, diferente do Postgres com POSTGRES_DB).
FROM mcr.microsoft.com/mssql/server:2025-latest
USER root
RUN apt-get update \
    && apt-get install -y curl \
    && curl -fsSL https://packages.microsoft.com/config/ubuntu/24.04/mssql-server-2025.list -o /etc/apt/sources.list.d/mssql-server-2025.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y mssql-server-fts \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
USER mssql
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
