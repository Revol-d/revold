#!/bin/bash
# Sobe o sqlservr normal E cria o banco "revold" sozinho no primeiro start -- a
# imagem oficial só cria o `master` (diferente do Postgres oficial, que cria o
# banco do `POSTGRES_DB` sozinho via variável de ambiente).
set -e

/opt/mssql/bin/sqlservr &
SQLSERVR_PID=$!

for _ in $(seq 1 60); do
    if /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -Q "SELECT 1" >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -Q \
    "IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = 'revold') CREATE DATABASE revold"

wait "$SQLSERVR_PID"
