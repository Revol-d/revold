"""Utilitários de teste compartilhados entre todos os cores/adapters do
monorepo (parte do "framework proprietário" — ver descrição do projeto).

Um módulo de fábricas por core (mesma convenção em todos, `factory_boy` +
`Faker("pt_BR")`), cada um só importando o domínio do seu próprio core
(nunca de outro — bounded contexts não compartilham modelo de domínio, ver
ADR-0002):

- `catalog_factories`: `Money`, `Category`, `ProductVariant`, `Product`.
- `cart_factories`: `Money` (própria de `cart`), `CartItem`, `Cart`.
- `inventory_factories`: `StockLevel`.
- `identity_factories`: `AuthenticatedUser`, `ApiKeyPrincipal`.
- `notification_factories`: `Notification`.
- `store_settings_factories`: `StoreSettings`.
- `events_factories`: `DomainEvent`.

É também o lugar certo para qualquer outra coisa de teste reutilizável
entre bounded contexts no futuro (ex. helpers de asserção).
"""
