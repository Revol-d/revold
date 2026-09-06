"""Utilitários de teste compartilhados entre todos os cores/adapters do
monorepo (parte do "framework proprietário" — ver descrição do projeto).

Hoje contém só fábricas de dados (`revold_testing.catalog_factories`), mas é
o lugar certo para qualquer coisa de teste reutilizável entre bounded
contexts no futuro (ex. builders de outros domínios, helpers de asserção).
"""
