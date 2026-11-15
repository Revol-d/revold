"""Teste de contrato leve do router de catalog: sobe o app FastAPI de verdade,
mas troca o repositório real pelo fake em memória via override de dependência
do FastAPI — não precisa de Postgres para validar o contrato HTTP.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import get_media_storage, get_product_repository
from api_gateway.main import app
from api_gateway.security import get_current_user
from revold_catalog.domain import Category, Money, Product, ProductVariant
from revold_identity.domain import AuthenticatedUser, Role


class _FakeRepository:
    def __init__(self) -> None:
        self._categories = {"camisetas": Category(slug="camisetas", name="Camisetas")}
        self._products = {
            "CAM-001": Product(
                sku="CAM-001",
                name="Camiseta Básica",
                category=Category(slug="camisetas", name="Camisetas"),
                price=Money(Decimal("79.90")),
                variants=[ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=True)],
                images=["https://example.com/cam-001.jpg"],
            )
        }

    async def list_categories(self):
        return list(self._categories.values())

    async def get_category(self, slug):
        return self._categories.get(slug)

    async def save_category(self, category):
        self._categories[category.slug] = category

    async def list_products(
        self,
        *,
        category_slug,
        page,
        page_size,
        search_query=None,
        sort="relevance",
        sizes=None,
        colors=None,
    ):
        items = list(self._products.values())
        if category_slug:
            items = [p for p in items if p.category.slug == category_slug]
        if search_query:
            needle = search_query.lower()
            items = [p for p in items if needle in p.name.lower()]
        if sizes or colors:
            items = [
                p
                for p in items
                if any(
                    (not sizes or v.size in sizes) and (not colors or v.color in colors)
                    for v in p.variants
                )
            ]
        items.sort(key=lambda p: p.sku)
        if sort == "price_asc":
            items.sort(key=lambda p: p.price.amount)
        elif sort == "price_desc":
            items.sort(key=lambda p: p.price.amount, reverse=True)
        return items, len(items)

    async def get_product(self, sku):
        return self._products.get(sku)

    async def save_product(self, product):
        self._products[product.sku] = product

    async def find_variant_owner(self, variant_sku):
        for product in self._products.values():
            if any(v.sku == variant_sku for v in product.variants):
                return product.sku
        return None

    async def delete_product(self, sku):
        self._products.pop(sku, None)

    async def delete_category(self, slug):
        self._categories.pop(slug, None)


class _FakeMediaStorage:
    """Fake em memória de MediaStorage (ADR-0015) — mesma convenção do
    resto deste arquivo: sem infra real, só pra validar o contrato HTTP."""

    def __init__(self) -> None:
        self.uploaded: dict[str, tuple[bytes, str]] = {}

    async def upload(self, *, key: str, content: bytes, content_type: str) -> str:
        self.uploaded[key] = (content, content_type)
        return f"https://fake-media.example.com/{key}"

    async def delete(self, key: str) -> None:
        self.uploaded.pop(key, None)


@pytest.fixture(autouse=True)
def override_media_storage():
    storage = _FakeMediaStorage()
    app.dependency_overrides[get_media_storage] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_media_storage, None)


_STAFF_USER = AuthenticatedUser(
    external_id="staff-1", provider="dev", email="staff@example.com", name="Staff",
    roles=(Role.STAFF,),
)
_CUSTOMER_USER = AuthenticatedUser(
    external_id="cust-1", provider="dev", email="cliente@example.com", name="Cliente",
    roles=(Role.CUSTOMER,),
)


@pytest.fixture(autouse=True)
def override_repository():
    # Uma única instância por teste: escritas (create_category/create_product)
    # precisam ser visíveis em leituras subsequentes na mesma requisição de
    # teste, então a mesma instância tem que ser devolvida a cada resolução.
    repository = _FakeRepository()
    app.dependency_overrides[get_product_repository] = lambda: repository
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_list_products(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["sku"] == "CAM-001"


async def test_list_products_busca_por_nome(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products", params={"q": "básica"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = await client.get("/api/catalog/products", params={"q": "vestido"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_list_products_sort_invalido_retorna_422(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products", params={"sort": "aleatorio"})
    assert response.status_code == 422


async def test_list_products_filtra_por_tamanho(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products", params={"size": ["P"]})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = await client.get("/api/catalog/products", params={"size": ["GG"]})
    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_list_products_filtra_por_cor(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products", params={"color": ["Branco"]})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = await client.get("/api/catalog/products", params={"color": ["Azul"]})
    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_list_products_tamanho_e_cor_combinados_exigem_mesma_variante(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/catalog/products", params={"size": ["P"], "color": ["Azul"]}
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_get_product_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products/NAO-EXISTE")
    assert response.status_code == 404


async def test_get_product_found(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products/CAM-001")
    assert response.status_code == 200
    assert response.json()["name"] == "Camiseta Básica"


async def test_create_category_sem_autenticacao_retorna_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/catalog/categories", json={"slug": "bolsas", "name": "Bolsas"}
    )
    assert response.status_code == 401


async def test_create_category_com_papel_customer_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.post(
        "/api/catalog/categories", json={"slug": "bolsas", "name": "Bolsas"}
    )
    assert response.status_code == 403


async def test_create_category_com_papel_staff_cria(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/categories", json={"slug": "bolsas", "name": "Bolsas"}
    )
    assert response.status_code == 201
    assert response.json() == {"slug": "bolsas", "name": "Bolsas"}


async def test_create_product_com_papel_staff_cria(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products",
        json={
            "sku": "VES-001",
            "name": "Vestido Floral",
            "category_slug": "camisetas",
            "price": {"amount": "129.90", "currency": "BRL"},
            "variants": [{"sku": "VES-001-M", "size": "M", "color": "Floral", "in_stock": True}],
        },
    )
    assert response.status_code == 201
    assert response.json()["sku"] == "VES-001"

    listed = await client.get("/api/catalog/products/VES-001")
    assert listed.status_code == 200


async def test_create_product_categoria_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products",
        json={
            "sku": "VES-002",
            "name": "Vestido",
            "category_slug": "nao-existe",
            "price": {"amount": "99.90", "currency": "BRL"},
        },
    )
    assert response.status_code == 404


async def test_create_product_sku_duplicado_retorna_409(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products",
        json={
            "sku": "CAM-001",
            "name": "Outra Camiseta",
            "category_slug": "camisetas",
            "price": {"amount": "59.90", "currency": "BRL"},
        },
    )
    assert response.status_code == 409


async def test_update_product_sem_autenticacao_retorna_401(client: AsyncClient) -> None:
    response = await client.patch("/api/catalog/products/CAM-001", json={"name": "X"})
    assert response.status_code == 401


async def test_update_product_com_papel_staff_atualiza_so_o_campo_enviado(
    client: AsyncClient,
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.patch(
        "/api/catalog/products/CAM-001", json={"name": "Camiseta Básica V2"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Camiseta Básica V2"
    assert body["price"]["amount"] == "79.90"  # não enviado, continua igual


async def test_update_product_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.patch("/api/catalog/products/NAO-EXISTE", json={"name": "X"})
    assert response.status_code == 404


async def test_update_product_categoria_nova_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.patch(
        "/api/catalog/products/CAM-001", json={"category_slug": "nao-existe"}
    )
    assert response.status_code == 404


async def test_add_product_variant_com_papel_staff_adiciona(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products/CAM-001/variants",
        json={"sku": "CAM-001-G-BR", "size": "G", "color": "Branco", "in_stock": True},
    )
    assert response.status_code == 201
    variantes = [v["sku"] for v in response.json()["variants"]]
    assert "CAM-001-G-BR" in variantes


async def test_add_product_variant_produto_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products/NAO-EXISTE/variants",
        json={"sku": "X-1", "size": "U", "color": "Preto"},
    )
    assert response.status_code == 404


async def test_add_product_variant_sku_duplicado_retorna_409(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products/CAM-001/variants",
        json={"sku": "CAM-001-P", "size": "P", "color": "Branco"},
    )
    assert response.status_code == 409


async def test_add_product_variant_com_papel_customer_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.post(
        "/api/catalog/products/CAM-001/variants",
        json={"sku": "CAM-001-GG", "size": "GG", "color": "Branco"},
    )
    assert response.status_code == 403


async def test_update_product_variant_com_papel_staff_atualiza(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.patch(
        "/api/catalog/products/CAM-001/variants/CAM-001-P",
        json={"in_stock": False},
    )
    assert response.status_code == 200
    variant = next(v for v in response.json()["variants"] if v["sku"] == "CAM-001-P")
    assert variant["in_stock"] is False
    assert variant["size"] == "P"


async def test_update_product_variant_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.patch(
        "/api/catalog/products/CAM-001/variants/NAO-EXISTE",
        json={"in_stock": False},
    )
    assert response.status_code == 404


async def test_update_product_variant_com_papel_customer_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.patch(
        "/api/catalog/products/CAM-001/variants/CAM-001-P",
        json={"in_stock": False},
    )
    assert response.status_code == 403


async def test_remove_product_variant_com_papel_staff_remove(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.delete("/api/catalog/products/CAM-001/variants/CAM-001-P")
    assert response.status_code == 200
    variantes = [v["sku"] for v in response.json()["variants"]]
    assert "CAM-001-P" not in variantes


async def test_remove_product_variant_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.delete("/api/catalog/products/CAM-001/variants/NAO-EXISTE")
    assert response.status_code == 404


async def test_remove_product_variant_com_papel_customer_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.delete("/api/catalog/products/CAM-001/variants/CAM-001-P")
    assert response.status_code == 403


async def test_delete_product_com_papel_staff_remove(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.delete("/api/catalog/products/CAM-001")
    assert response.status_code == 204

    seguinte = await client.get("/api/catalog/products/CAM-001")
    assert seguinte.status_code == 404


async def test_delete_product_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.delete("/api/catalog/products/NAO-EXISTE")
    assert response.status_code == 404


async def test_delete_product_com_papel_customer_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.delete("/api/catalog/products/CAM-001")
    assert response.status_code == 403


async def test_delete_category_com_produtos_retorna_409(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.delete("/api/catalog/categories/camisetas")
    assert response.status_code == 409


async def test_delete_category_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.delete("/api/catalog/categories/nao-existe")
    assert response.status_code == 404


async def test_delete_category_sem_produtos_remove(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    criada = await client.post(
        "/api/catalog/categories", json={"slug": "acessorios", "name": "Acessórios"}
    )
    assert criada.status_code == 201

    response = await client.delete("/api/catalog/categories/acessorios")
    assert response.status_code == 204


async def test_delete_category_com_papel_customer_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.delete("/api/catalog/categories/camisetas")
    assert response.status_code == 403


async def test_add_product_image_com_papel_staff_faz_upload_e_anexa_url(
    client: AsyncClient, override_media_storage: _FakeMediaStorage
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products/CAM-001/images",
        files={"file": ("foto.jpg", b"conteudo-fake-da-foto", "image/jpeg")},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["images"]) == 2  # já tinha 1, ganhou mais 1
    nova_url = body["images"][-1]
    assert nova_url.startswith("https://fake-media.example.com/products/CAM-001/")
    assert nova_url.endswith("-foto.jpg")

    # confirma que o conteúdo/bytes foram realmente repassados ao MediaStorage
    (content, content_type), = [
        v for k, v in override_media_storage.uploaded.items() if k in nova_url
    ]
    assert content == b"conteudo-fake-da-foto"
    assert content_type == "image/jpeg"


async def test_add_product_image_sanitiza_nome_de_arquivo_perigoso(
    client: AsyncClient, override_media_storage: _FakeMediaStorage
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products/CAM-001/images",
        files={"file": ("../../etc/passwd.jpg", b"x", "image/jpeg")},
    )
    assert response.status_code == 201
    nova_url = response.json()["images"][-1]
    # a sanitização (revold_catalog.application.use_cases._UNSAFE_FILENAME_CHARS) troca
    # cada sequência de "/" por "_", então o nome vira um único segmento
    # sem barra nenhuma — impossível "escapar" do diretório
    # products/{sku}/ mesmo contendo ".." literais, já que não sobra "/"
    # para formar um caminho novo (ver LocalFilesystemStorage.upload, que
    # faz base_dir / key sem outra validação).
    assert nova_url.startswith("https://fake-media.example.com/products/CAM-001/")
    caminho_apos_prefixo = nova_url.removeprefix(
        "https://fake-media.example.com/products/CAM-001/"
    )
    assert "/" not in caminho_apos_prefixo
    assert caminho_apos_prefixo.endswith("-.._.._etc_passwd.jpg")


async def test_add_product_image_tipo_nao_suportado_retorna_422(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products/CAM-001/images",
        files={"file": ("arquivo.txt", b"nao e imagem", "text/plain")},
    )
    assert response.status_code == 422


async def test_add_product_image_maior_que_limite_retorna_422(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    conteudo_grande = b"x" * (10 * 1024 * 1024 + 1)
    response = await client.post(
        "/api/catalog/products/CAM-001/images",
        files={"file": ("grande.jpg", conteudo_grande, "image/jpeg")},
    )
    assert response.status_code == 422


async def test_add_product_image_produto_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post(
        "/api/catalog/products/NAO-EXISTE/images",
        files={"file": ("foto.jpg", b"x", "image/jpeg")},
    )
    assert response.status_code == 404


async def test_add_product_image_sem_autenticacao_retorna_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/catalog/products/CAM-001/images",
        files={"file": ("foto.jpg", b"x", "image/jpeg")},
    )
    assert response.status_code == 401


async def test_add_product_image_com_papel_customer_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.post(
        "/api/catalog/products/CAM-001/images",
        files={"file": ("foto.jpg", b"x", "image/jpeg")},
    )
    assert response.status_code == 403
