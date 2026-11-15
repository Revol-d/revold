"""Dado de demonstração ("seed semântico") de `revold_catalog` — ver ADR-0022.

Isto é diferente de `tests/support/*_factories.py` (Factory Boy + Faker,
dado realista mas ALEATÓRIO e deliberadamente cheio de caso de borda —
acento, emoji, parágrafo vazio, preço quebrado — pensado pra exercitar
teste automatizado). O conteúdo abaixo é escrito à mão, fixo e coerente:
é o catálogo que a Nick e qualquer visitante veem quando alguém precisa
avaliar como o site *fica de verdade* com dado dentro — um nome de
produto com emoji não é "dado realista" numa vitrine, é falha de
conteúdo. Nada aqui usa Faker.

Contrato do módulo (ver `revold_ecommerce.application.seed`, no produto): qualquer
domínio com dado de demonstração relevante pro storefront/admin expõe, neste
mesmo nome de arquivo (`seed.py`), constantes prontas para o orquestrador
central consumir — aqui `CATEGORIES` e `PRODUCTS`. Um core novo não
aprende nenhuma API de seed: só descreve o próprio dado no formato que já
entende (dataclasses de domínio, como `Category`/`Product` abaixo), e o
orquestrador persiste através dos repositórios reais — nunca INSERT cru,
sempre os mesmos objetos de domínio que uma chamada de admin real geraria,
o que garante as mesmas invariantes (`Money` não aceita negativo, etc.)
sem o seed precisar reimplementá-las.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from revold_catalog.domain import Category, Money, Product, ProductVariant


@dataclass(frozen=True, slots=True)
class SeedVariant:
    """Uma variante de demonstração + quanto estoque físico ela deve ter.

    `initial_stock` não existe em `ProductVariant` — `revold_catalog` não
    conhece estoque, é `revold_inventory` que conhece (ADR-0002, cores
    isolados). É lido só pelo orquestrador do seed, que separadamente
    chama `revold_inventory.ReceiveStock`. Já `in_stock` É o mesmo campo de
    `ProductVariant`: um flag editado à mão pela Nick/staff no admin (é o
    que o storefront usa pra mostrar "esgotado" — de propósito
    independente da quantidade física, ver revold_inventory/seed seguinte).
    """

    size: str
    color: str
    variant_sku: str
    in_stock: bool = True
    initial_stock: int = 20


@dataclass(frozen=True, slots=True)
class SeedProduct:
    sku: str
    name: str
    category_slug: str
    price: str
    description: str
    images: tuple[str, ...]
    variants: tuple[SeedVariant, ...]
    original_price: str | None = None

    def to_domain(self, category: Category) -> Product:
        return Product(
            sku=self.sku,
            name=self.name,
            category=category,
            price=Money(amount=Decimal(self.price)),
            variants=[
                ProductVariant(sku=v.variant_sku, size=v.size, color=v.color, in_stock=v.in_stock)
                for v in self.variants
            ],
            images=list(self.images),
            description=self.description,
            original_price=Money(amount=Decimal(self.original_price)) if self.original_price else None,
        )


def _img(seed: str) -> str:
    """Placeholder determinístico (mesma SKU sempre gera a mesma imagem).
    Troque pelo upload real assim que a Nick tiver fotos do produto (ver
    `MediaStorage` em `revold_catalog.ports`) — o único objetivo aqui é nunca
    deixar a vitrine com espaço em branco no lugar da foto durante a
    avaliação/demo."""
    return f"https://picsum.photos/seed/revold-{seed}/800/1000"


CATEGORIES: tuple[Category, ...] = (
    Category(slug="camisetas", name="Camisetas"),
    Category(slug="vestidos", name="Vestidos"),
    Category(slug="calcas", name="Calças"),
    Category(slug="jaquetas-e-casacos", name="Jaquetas e Casacos"),
    Category(slug="calcados", name="Calçados"),
    Category(slug="acessorios", name="Acessórios"),
)

PRODUCTS: tuple[SeedProduct, ...] = (
    # -- Camisetas --------------------------------------------------
    SeedProduct(
        sku="CAM-001",
        name="Camiseta Básica Algodão Pima",
        category_slug="camisetas",
        price="69.90",
        description="Camiseta de algodão pima, corte reto e caimento leve — o básico que não sai de moda.",
        images=(_img("cam-001"),),
        variants=(
            SeedVariant(size="P", color="Branco", variant_sku="CAM-001-P-BRANCO"),
            SeedVariant(size="M", color="Branco", variant_sku="CAM-001-M-BRANCO"),
            SeedVariant(size="M", color="Preto", variant_sku="CAM-001-M-PRETO"),
            SeedVariant(size="G", color="Preto", variant_sku="CAM-001-G-PRETO"),
        ),
    ),
    SeedProduct(
        sku="CAM-002",
        name="Camiseta Estampada Folhagem",
        category_slug="camisetas",
        price="89.90",
        original_price="109.90",
        description="Estampa botânica exclusiva em algodão macio — a queridinha da coleção atual, em promoção.",
        images=(_img("cam-002"),),
        variants=(
            SeedVariant(size="P", color="Verde Musgo", variant_sku="CAM-002-P-VERDE"),
            SeedVariant(size="M", color="Verde Musgo", variant_sku="CAM-002-M-VERDE"),
            SeedVariant(size="M", color="Bege", variant_sku="CAM-002-M-BEGE"),
        ),
    ),
    SeedProduct(
        sku="CAM-003",
        name="Camiseta Gola V Modal",
        category_slug="camisetas",
        price="79.90",
        description="Tecido modal com toque sedoso e caimento fluido, gola V discreta.",
        images=(_img("cam-003"),),
        variants=(
            SeedVariant(size="P", color="Vinho", variant_sku="CAM-003-P-VINHO"),
            SeedVariant(size="M", color="Vinho", variant_sku="CAM-003-M-VINHO"),
        ),
    ),
    SeedProduct(
        sku="CAM-004",
        name="Camiseta Oversized Manga Longa",
        category_slug="camisetas",
        price="99.90",
        description="Modelagem oversized, manga longa, ideal pra dias mais frescos sem abrir mão do conforto.",
        images=(_img("cam-004"),),
        variants=(
            SeedVariant(size="M", color="Cinza Mescla", variant_sku="CAM-004-M-CINZA"),
            SeedVariant(
                size="G", color="Cinza Mescla", variant_sku="CAM-004-G-CINZA",
                in_stock=False, initial_stock=0,
            ),
        ),
    ),
    # -- Vestidos -----------------------------------------------------
    SeedProduct(
        sku="VES-001",
        name="Vestido Midi Alfaiataria",
        category_slug="vestidos",
        price="219.90",
        description="Corte alfaiataria em tecido estruturado, comprimento midi — do escritório ao happy hour.",
        images=(_img("ves-001"),),
        variants=(
            SeedVariant(size="P", color="Preto", variant_sku="VES-001-P-PRETO"),
            SeedVariant(size="M", color="Preto", variant_sku="VES-001-M-PRETO"),
            SeedVariant(size="M", color="Azul Marinho", variant_sku="VES-001-M-AZUL"),
        ),
    ),
    SeedProduct(
        sku="VES-002",
        name="Vestido Longo Estampa Floral",
        category_slug="vestidos",
        price="259.90",
        original_price="299.90",
        description="Vestido longo fluido com estampa floral exclusiva, alças reguláveis.",
        images=(_img("ves-002"),),
        variants=(
            SeedVariant(size="P", color="Floral", variant_sku="VES-002-P-FLORAL"),
            SeedVariant(size="M", color="Floral", variant_sku="VES-002-M-FLORAL"),
        ),
    ),
    SeedProduct(
        sku="VES-003",
        name="Vestido Curto Linho",
        category_slug="vestidos",
        price="189.90",
        description="Linho puro, caimento solto e fresco — a escolha certa pros dias mais quentes.",
        images=(_img("ves-003"),),
        variants=(
            SeedVariant(
                size="P", color="Bege", variant_sku="VES-003-P-BEGE",
                initial_stock=3,
            ),
            SeedVariant(size="M", color="Bege", variant_sku="VES-003-M-BEGE"),
        ),
    ),
    SeedProduct(
        sku="VES-004",
        name="Vestido Tubinho Preto",
        category_slug="vestidos",
        price="199.90",
        description="O clássico que toda mulher tem no armário — versátil, de dia ou de noite.",
        images=(_img("ves-004"),),
        variants=(
            SeedVariant(size="P", color="Preto", variant_sku="VES-004-P-PRETO"),
            SeedVariant(size="M", color="Preto", variant_sku="VES-004-M-PRETO"),
            SeedVariant(size="G", color="Preto", variant_sku="VES-004-G-PRETO"),
        ),
    ),
    # -- Calças ---------------------------------------------------------
    SeedProduct(
        sku="CAL-001",
        name="Calça Jeans Reta Cintura Alta",
        category_slug="calcas",
        price="189.90",
        description="Jeans com elastano, cintura alta e caimento reto — o coringa do guarda-roupa.",
        images=(_img("cal-001"),),
        variants=(
            SeedVariant(size="36", color="Azul Escuro", variant_sku="CAL-001-36-AZUL"),
            SeedVariant(size="38", color="Azul Escuro", variant_sku="CAL-001-38-AZUL"),
            SeedVariant(size="40", color="Azul Escuro", variant_sku="CAL-001-40-AZUL"),
        ),
    ),
    SeedProduct(
        sku="CAL-002",
        name="Calça Alfaiataria Pantalona",
        category_slug="calcas",
        price="219.90",
        description="Pantalona de alfaiataria com pence frontal, tecido com caimento fluido.",
        images=(_img("cal-002"),),
        variants=(
            SeedVariant(size="P", color="Preto", variant_sku="CAL-002-P-PRETO"),
            SeedVariant(size="M", color="Preto", variant_sku="CAL-002-M-PRETO"),
        ),
    ),
    SeedProduct(
        sku="CAL-003",
        name="Calça Legging Térmica",
        category_slug="calcas",
        price="129.90",
        description="Legging térmica de alta compressão, cintura alta — treino ou dia a dia.",
        images=(_img("cal-003"),),
        variants=(
            SeedVariant(size="P", color="Preto", variant_sku="CAL-003-P-PRETO"),
            SeedVariant(size="M", color="Preto", variant_sku="CAL-003-M-PRETO"),
        ),
    ),
    SeedProduct(
        sku="CAL-004",
        name="Calça Cargo Sarja",
        category_slug="calcas",
        price="199.90",
        description="Sarja resistente, bolsos cargo funcionais, modelagem reta.",
        images=(_img("cal-004"),),
        variants=(
            SeedVariant(size="38", color="Verde Musgo", variant_sku="CAL-004-38-VERDE"),
            SeedVariant(
                size="40", color="Verde Musgo", variant_sku="CAL-004-40-VERDE",
                in_stock=False, initial_stock=0,
            ),
        ),
    ),
    # -- Jaquetas e Casacos ----------------------------------------------
    SeedProduct(
        sku="JAQ-001",
        name="Jaqueta Jeans Clássica",
        category_slug="jaquetas-e-casacos",
        price="249.90",
        description="Jaqueta jeans tradicional, lavagem média, forro em algodão.",
        images=(_img("jaq-001"),),
        variants=(
            SeedVariant(size="P", color="Azul Médio", variant_sku="JAQ-001-P-AZUL"),
            SeedVariant(size="M", color="Azul Médio", variant_sku="JAQ-001-M-AZUL"),
        ),
    ),
    SeedProduct(
        sku="JAQ-002",
        name="Casaco Trench Coat",
        category_slug="jaquetas-e-casacos",
        price="379.90",
        original_price="449.90",
        description="Trench coat impermeável com cinto de amarrar, forro xadrez removível.",
        images=(_img("jaq-002"),),
        variants=(
            SeedVariant(size="M", color="Bege", variant_sku="JAQ-002-M-BEGE"),
            SeedVariant(size="G", color="Bege", variant_sku="JAQ-002-G-BEGE"),
        ),
    ),
    SeedProduct(
        sku="JAQ-003",
        name="Jaqueta Corta-Vento",
        category_slug="jaquetas-e-casacos",
        price="199.90",
        description="Corta-vento leve e dobrável, ideal pra levar na bolsa pro final de tarde.",
        images=(_img("jaq-003"),),
        variants=(
            SeedVariant(size="P", color="Preto", variant_sku="JAQ-003-P-PRETO"),
            SeedVariant(size="M", color="Preto", variant_sku="JAQ-003-M-PRETO"),
        ),
    ),
    # -- Calçados ---------------------------------------------------------
    SeedProduct(
        sku="CAD-001",
        name="Tênis Casual Couro Sintético",
        category_slug="calcados",
        price="259.90",
        description="Tênis casual em couro sintético, solado emborrachado antiderrapante.",
        images=(_img("cad-001"),),
        variants=(
            SeedVariant(size="37", color="Branco", variant_sku="CAD-001-37-BRANCO"),
            SeedVariant(size="38", color="Branco", variant_sku="CAD-001-38-BRANCO"),
            SeedVariant(size="39", color="Branco", variant_sku="CAD-001-39-BRANCO"),
        ),
    ),
    SeedProduct(
        sku="CAD-002",
        name="Bota Coturno",
        category_slug="calcados",
        price="289.90",
        description="Coturno em couro legítimo, cadarço reforçado, solado tratorado.",
        images=(_img("cad-002"),),
        variants=(
            SeedVariant(size="37", color="Preto", variant_sku="CAD-002-37-PRETO"),
            SeedVariant(size="38", color="Preto", variant_sku="CAD-002-38-PRETO"),
        ),
    ),
    SeedProduct(
        sku="CAD-003",
        name="Sandália Rasteira Tiras",
        category_slug="calcados",
        price="119.90",
        description="Rasteira com tiras finas entrelaçadas, fivela ajustável no tornozelo.",
        images=(_img("cad-003"),),
        variants=(
            SeedVariant(
                size="36", color="Dourado", variant_sku="CAD-003-36-DOURADO",
                initial_stock=2,
            ),
            SeedVariant(size="37", color="Dourado", variant_sku="CAD-003-37-DOURADO"),
        ),
    ),
    # -- Acessórios ---------------------------------------------------------
    SeedProduct(
        sku="ACE-001",
        name="Bolsa Tote Lona",
        category_slug="acessorios",
        price="149.90",
        description="Bolsa tote em lona resistente, alças reforçadas, bolso interno com zíper.",
        images=(_img("ace-001"),),
        variants=(SeedVariant(size="Único", color="Bege", variant_sku="ACE-001-U-BEGE"),),
    ),
    SeedProduct(
        sku="ACE-002",
        name="Cinto Couro Fivela Dourada",
        category_slug="acessorios",
        price="79.90",
        description="Cinto de couro legítimo com fivela dourada, largura 3cm.",
        images=(_img("ace-002"),),
        variants=(
            SeedVariant(size="P/M", color="Preto", variant_sku="ACE-002-PM-PRETO"),
            SeedVariant(size="G/GG", color="Preto", variant_sku="ACE-002-GG-PRETO"),
        ),
    ),
    SeedProduct(
        sku="ACE-003",
        name="Óculos de Sol Redondo",
        category_slug="acessorios",
        price="99.90",
        description="Armação redonda estilo retrô, lente com proteção UV400.",
        images=(_img("ace-003"),),
        variants=(SeedVariant(size="Único", color="Preto", variant_sku="ACE-003-U-PRETO"),),
    ),
)
