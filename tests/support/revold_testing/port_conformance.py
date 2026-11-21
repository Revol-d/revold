"""Funções de conformidade de porta: uma função por porta tocada pela migração
Postgres -> Azure SQL (ver o plano em docs internos), que QUALQUER adapter que diz
implementar aquela porta precisa passar. É a prova mecânica de que dois adapters
diferentes (ou um fake) se comportam do mesmo jeito -- antes desta migração, nenhuma
porta do repositório tinha isso: cada adapter só tinha o próprio teste bespoke, e os
fakes de teste nunca eram verificados contra o adapter real.

Escopo: só as portas tocadas por esta migração, não um framework genérico para todas as
portas do repositório (over-engineering fora do que a migração precisa).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from revold_ai_assistant.ports import ProductIndex
from revold_catalog.domain import Category, Product, ProductVariant
from revold_catalog.domain import Money as CatalogMoney
from revold_catalog.ports import ProductRepository
from revold_testing.catalog_factories import ProductFactory
from revold_identity.domain import ApiKeyNotFound
from revold_identity.ports import ApiKeyAuth
from revold_inventory.ports import InventoryRepository
from revold_orders.domain import Money, Order, OrderLine, PaymentStatus
from revold_orders.ports import OrderRepository
from revold_payments.domain import Charge
from revold_payments.domain import Money as PaymentMoney
from revold_payments.domain import PaymentMethod
from revold_payments.ports import ChargeRepository
from revold_store_settings.ports import StoreSettingsRepository
from revold_testing.inventory_factories import StockLevelFactory
from revold_testing.store_settings_factories import StoreSettingsFactory


async def assert_store_settings_repository_conformance(
    repository: StoreSettingsRepository,
) -> None:
    """Qualquer StoreSettingsRepository (Postgres, Azure SQL, fake em memória)
    precisa passar por isto. Assume o repositório vazio ao receber (quem chama cuida
    de limpar o estado antes, ver as fixtures `repository` de cada teste de
    integração)."""
    assert await repository.get() is None

    first = StoreSettingsFactory()
    await repository.save(first)
    assert await repository.get() == first

    second = StoreSettingsFactory()
    await repository.save(second)
    reloaded = await repository.get()
    assert reloaded == second
    assert reloaded != first


async def assert_inventory_repository_conformance(repository: InventoryRepository) -> None:
    """Qualquer InventoryRepository (Postgres, Azure SQL, fake em memória) precisa
    passar por isto. Usa um SKU próprio (`StockLevelFactory` gera um aleatório) para
    não colidir com outros registros que já estejam no repositório."""
    stock = StockLevelFactory()

    assert await repository.get(stock.sku) is None

    await repository.save(stock)
    assert await repository.get(stock.sku) == stock

    stock.receive(10)
    await repository.save(stock)
    reloaded = await repository.get(stock.sku)
    assert reloaded == stock
    assert reloaded.quantity_on_hand == stock.quantity_on_hand


def _build_order(order_id: str) -> Order:
    return Order(
        order_id=order_id,
        cart_id="c1",
        lines=(
            OrderLine(
                sku="A",
                product_name="Camiseta",
                variant_label="M / Azul",
                unit_price=Money(Decimal("59.90")),
                quantity=2,
            ),
            OrderLine(
                sku="B",
                product_name="Calça",
                variant_label="42",
                unit_price=Money(Decimal("120.00")),
                quantity=1,
            ),
        ),
        created_at="2026-09-12T10:00:00+00:00",
    )


async def assert_order_repository_conformance(repository: OrderRepository) -> None:
    """Qualquer OrderRepository (Postgres, Azure SQL, fake em memória) precisa passar
    por isto. Assume o repositório vazio ao receber."""
    assert await repository.get("nao-existe") is None

    order = _build_order("o-pago")
    await repository.save(order)
    reloaded = await repository.get(order.order_id)
    assert reloaded is not None
    assert [line.sku for line in reloaded.lines] == ["A", "B"]
    assert reloaded.total() == Money(Decimal("239.80"))
    assert reloaded.payment_status == PaymentStatus.PENDING

    reloaded.mark_paid()
    await repository.save(reloaded)
    reloaded_again = await repository.get(order.order_id)
    assert reloaded_again is not None
    assert reloaded_again.payment_status == PaymentStatus.PAID
    assert len(reloaded_again.lines) == 2  # não duplicou

    await repository.save(_build_order("o-pendente"))

    only_paid, total_paid = await repository.list(
        payment_status=PaymentStatus.PAID, page=1, page_size=20
    )
    assert total_paid == 1
    assert only_paid[0].order_id == "o-pago"

    all_orders, total_all = await repository.list(payment_status=None, page=1, page_size=1)
    assert total_all == 2
    assert len(all_orders) == 1


def _build_charge(charge_id: str, order_id: str, *, created_at: str) -> Charge:
    return Charge(
        charge_id=charge_id,
        order_id=order_id,
        provider="mercado_pago",
        provider_charge_id=f"mp-{charge_id}",
        method=PaymentMethod.PIX,
        amount=PaymentMoney(Decimal("59.90")),
        pix_qr_code="qr-fake",
        pix_copy_paste="copia-e-cola-fake",
        created_at=created_at,
    )


async def assert_charge_repository_conformance(repository: ChargeRepository) -> None:
    """Qualquer ChargeRepository (Postgres, Azure SQL, fake em memória) precisa
    passar por isto. Assume o repositório vazio ao receber."""
    assert await repository.get("nao-existe") is None

    first = _build_charge("ch1", "o1", created_at="2026-09-12T10:00:00+00:00")
    await repository.save(first)
    reloaded = await repository.get(first.charge_id)
    assert reloaded is not None
    assert reloaded.order_id == "o1"
    assert reloaded.amount == PaymentMoney(Decimal("59.90"))
    assert reloaded.pix_qr_code == "qr-fake"

    second = _build_charge("ch2", "o1", created_at="2026-09-12T11:00:00+00:00")
    await repository.save(second)
    most_recent = await repository.get_by_order("o1")
    assert most_recent is not None
    assert most_recent.charge_id == "ch2"

    found = await repository.get_by_provider_charge_id("mp-ch1")
    assert found is not None
    assert found.charge_id == "ch1"

    reloaded.mark_paid()
    await repository.save(reloaded)
    reloaded_again = await repository.get(first.charge_id)
    assert reloaded_again is not None
    assert reloaded_again.status.value == "paid"


async def assert_api_key_auth_conformance(auth: ApiKeyAuth) -> None:
    """Qualquer ApiKeyAuth (Postgres, Azure SQL, fake em memória) precisa passar por
    isto."""
    principal, raw_key = await auth.issue(name="Parceiro ERP")
    assert raw_key.startswith("rvld_")
    assert principal.name == "Parceiro ERP"

    resolved = await auth.resolve(raw_key)
    assert resolved == principal

    assert await auth.resolve("rvld_nao-existe") is None

    await auth.revoke(principal.key_id)
    assert await auth.resolve(raw_key) is None

    with pytest.raises(ApiKeyNotFound):
        await auth.revoke("nao-existe")

    _, raw_key_a = await auth.issue(name="Parceiro A")
    _, raw_key_b = await auth.issue(name="Parceiro B")
    assert raw_key_a != raw_key_b


async def assert_product_repository_conformance(repository: ProductRepository) -> None:
    """Qualquer ProductRepository (Postgres, Azure SQL, fake em memória) precisa
    passar por isto. **Não cobre busca full-text** -- o ranking de relevância é
    definido por adapter (ver docstring da porta e ADR da migração), então os
    testes de busca ficam no arquivo de integração de cada adapter, não aqui.
    Assume o repositório vazio ao receber."""
    assert await repository.get_category("nao-existe") is None
    assert await repository.list_categories() == []

    category = Category(slug="camisetas", name="Camisetas")
    await repository.save_category(category)
    assert await repository.get_category("camisetas") == category
    assert await repository.list_categories() == [category]

    product = Product(
        sku="CAM-001",
        name="Camiseta Básica",
        category=category,
        price=CatalogMoney(Decimal("79.90")),
        variants=[ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=True)],
        images=["https://example.com/a.jpg"],
    )
    await repository.save_product(product)
    reloaded = await repository.get_product("CAM-001")
    assert reloaded is not None
    assert reloaded.price.amount == Decimal("79.90")
    assert len(reloaded.variants) == 1
    assert reloaded.variants[0].sku == "CAM-001-P"

    # Reconciliação de variantes por SKU (não recria do zero) -- o bug real que só
    # aparece contra SQL de verdade (conflito de PK), nunca contra um fake.
    updated = Product(
        sku="CAM-001",
        name="Camiseta Básica",
        category=category,
        price=CatalogMoney(Decimal("89.90")),
        variants=[
            ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=False),
            ProductVariant(sku="CAM-001-M", size="M", color="Branco", in_stock=True),
        ],
    )
    await repository.save_product(updated)  # não deve levantar IntegrityError
    reloaded = await repository.get_product("CAM-001")
    assert reloaded is not None
    variants_by_sku = {v.sku: v for v in reloaded.variants}
    assert variants_by_sku["CAM-001-P"].in_stock is False
    assert variants_by_sku["CAM-001-M"].in_stock is True

    # Remover variante via save_product apaga a linha de verdade.
    without_m = Product(
        sku="CAM-001",
        name="Camiseta Básica",
        category=category,
        price=CatalogMoney(Decimal("89.90")),
        variants=[ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=False)],
    )
    await repository.save_product(without_m)
    reloaded = await repository.get_product("CAM-001")
    assert reloaded is not None
    assert [v.sku for v in reloaded.variants] == ["CAM-001-P"]
    assert await repository.find_variant_owner("CAM-001-M") is None

    # Preço: ordenação via ORDER BY de verdade.
    barato = Product(
        sku="CAM-BARATO", name="Barata", category=category, price=CatalogMoney(Decimal("29.90")), variants=[]
    )
    caro = Product(
        sku="CAM-CARO", name="Cara", category=category, price=CatalogMoney(Decimal("199.90")), variants=[]
    )
    await repository.save_product(caro)
    await repository.save_product(barato)
    items, total = await repository.list_products(
        category_slug=None, page=1, page_size=20, sort="price_asc"
    )
    assert total == 3  # CAM-001 + CAM-BARATO + CAM-CARO
    baratos_primeiro = [p.sku for p in items if p.sku in ("CAM-BARATO", "CAM-CARO")]
    assert baratos_primeiro == ["CAM-BARATO", "CAM-CARO"]

    # Filtro por tamanho/cor via EXISTS -- tamanho+cor juntos exigem a MESMA variante.
    await repository.save_product(
        Product(
            sku="CAL-001",
            name="Calça Jeans",
            category=category,
            price=CatalogMoney(Decimal("120")),
            variants=[ProductVariant(sku="CAL-001-38", size="38", color="Azul", in_stock=True)],
        )
    )
    items, total = await repository.list_products(
        category_slug=None, page=1, page_size=20, sizes=["38"], colors=["Azul"]
    )
    assert total == 1
    assert items[0].sku == "CAL-001"
    items, total = await repository.list_products(
        category_slug=None, page=1, page_size=20, sizes=["38"], colors=["Branco"]
    )
    assert total == 0  # "38" existe (CAL-001) mas não na cor Branco -- não deve casar

    # Delete: produto some com as variantes (cascade); categoria some; idempotente.
    await repository.delete_product("CAM-001")
    assert await repository.get_product("CAM-001") is None
    assert await repository.find_variant_owner("CAM-001-P") is None
    await repository.delete_product("NAO-EXISTE")  # idempotente, sem erro

    await repository.save_category(Category(slug="acessorios", name="Acessórios"))
    await repository.delete_category("acessorios")
    assert await repository.get_category("acessorios") is None


async def assert_product_repository_bulk_roundtrip(repository: ProductRepository) -> None:
    """Lote de produtos gerados por fábrica (Faker), não fixture limpa escrita à
    mão -- pega problema de precisão/encoding que nem o fake em memória nem uma
    fixture "CAM-001" testariam. Precisa de uma categoria já salva (`category`)."""
    category = Category(slug="camisetas-bulk", name="Camisetas")
    await repository.save_category(category)

    produtos = [ProductFactory(category=category) for _ in range(15)]
    for produto in produtos:
        await repository.save_product(produto)

    for produto in produtos:
        reloaded = await repository.get_product(produto.sku)
        assert reloaded is not None
        assert reloaded.price.amount == produto.price.amount
        assert reloaded.name == produto.name
        assert {v.sku for v in reloaded.variants} == {v.sku for v in produto.variants}

    unicode_produto = ProductFactory(
        category=category, name="Vestido Midi Ção 🎉", description=""
    )
    await repository.save_product(unicode_produto)
    reloaded = await repository.get_product(unicode_produto.sku)
    assert reloaded is not None
    assert reloaded.name == "Vestido Midi Ção 🎉"
    assert reloaded.description == ""


# Mesma dimensão do text-embedding-3-small (Azure OpenAI) que os dois adapters usam --
# ver revold_ai_assistant.adapters.*.models.EMBEDDING_DIMENSIONS e ADR-0011. Repetida
# aqui (não importada de um adapter específico) para não criar uma dependência
# assimétrica entre os dois adapters dentro do harness compartilhado.
_EMBEDDING_DIMENSIONS = 1536


def _basis_vector(dimension_with_one: int) -> list[float]:
    """Vetor com 1.0 numa posição e 0.0 no resto -- dá pra prever a distância de
    cosseno exata entre dois destes (0.0 se mesma posição, 1.0 se diferente), sem
    depender de embedding real."""
    vector = [0.0] * _EMBEDDING_DIMENSIONS
    vector[dimension_with_one] = 1.0
    return vector


async def assert_product_index_conformance(index: ProductIndex) -> None:
    """Qualquer ProductIndex (Postgres+pgvector, Azure SQL+VECTOR/DiskANN, fake em
    memória) precisa passar por isto. Assume o índice vazio ao receber."""
    assert await index.search(embedding=_basis_vector(0), limit=5) == []

    await index.upsert(
        sku="CAM-001", name="Camiseta v1", description="descrição antiga", embedding=_basis_vector(0)
    )
    await index.upsert(
        sku="CAM-001", name="Camiseta v2", description="descrição nova", embedding=_basis_vector(1)
    )
    resultados = await index.search(embedding=_basis_vector(1), limit=10)
    assert len(resultados) == 1  # upsert atualiza, não duplica
    assert resultados[0].name == "Camiseta v2"

    await index.upsert(sku="A", name="Produto A", description="", embedding=_basis_vector(0))
    await index.upsert(sku="B", name="Produto B", description="", embedding=_basis_vector(1))
    await index.upsert(sku="C", name="Produto C", description="", embedding=_basis_vector(2))
    # CAM-001 também está no índice com o vetor de dimensão 1 -- junto de B.
    resultados = await index.search(embedding=_basis_vector(1), limit=10)
    assert resultados[0].distance == pytest.approx(0.0, abs=1e-6)
    assert resultados[0].sku in ("B", "CAM-001")

    resultados = await index.search(embedding=_basis_vector(0), limit=2)
    assert len(resultados) == 2  # limit restringe quantidade
