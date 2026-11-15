# API

Contratos OpenAPI ficam em `products/ecommerce/contracts/api/`. O primeiro contrato implementado é `products/ecommerce/contracts/api/catalog.yaml`, servido por `apps/ecommerce/api-gateway`.

Convenção: nenhum endpoint é implementado sem o contrato correspondente já existir em `products/ecommerce/contracts/api/` (Contract-First, ver ADR-0002).
