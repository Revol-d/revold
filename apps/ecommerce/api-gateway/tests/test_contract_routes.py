"""Gate de contrato: a API e os contratos OpenAPI descrevem as mesmas rotas.

A convenção do projeto é Contract-First (docs/api/README.md): nenhuma rota existe sem o contrato
em `products/ecommerce/contracts/api/`, que é o cardápio que os sites consultam. Até aqui, só a
revisão conferia isso. Este teste compara o método e o caminho de cada rota da API com os dos
contratos e reprova as duas divergências: rota sem contrato e contrato de rota que não existe.

O que ele NÃO confere: os campos de cada requisição e resposta. Isso fica para outra etapa
(CONTRIBUTING.md, seção 13, item 12).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI

from api_gateway.main import app

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[4]
CONTRACTS_DIR = ROOT / "products" / "ecommerce" / "contracts" / "api"
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete"})

# Rotas da API que, de propósito, não estão em contrato nenhum: são da operação, não do cliente.
# Cada uma precisa de motivo; a lista não cresce sem discussão.
OUTSIDE_CONTRACT: dict[tuple[str, str], str] = {
    ("GET", "/health"): "liveness do orquestrador de containers, não é rota de cliente",
    ("GET", "/metrics"): "scrape do Prometheus (ADR-0017), fica na rede interna",
}

Route = tuple[str, str]


def _normalize(path: str) -> str:
    """`/api/cart/{cart_id}/items/` e `/api/cart/{id}/items` são a mesma rota."""
    return re.sub(r"\{[^}]+\}", "{}", path.rstrip("/")) or "/"


def api_routes(application: FastAPI) -> set[Route]:
    """Método e caminho de cada rota que a API publica no OpenAPI dela."""
    routes = set()
    for path, operations in application.openapi()["paths"].items():
        for method in operations:
            routes.add((method.upper(), _normalize(path)))
    return routes


def _base_path(document: dict) -> str:
    """O prefixo do primeiro `servers` do contrato (`/api/cart`), sem esquema nem host."""
    servers = document.get("servers") or []
    if not servers:
        return ""
    match = re.match(r"^(?:https?://[^/]+)?(/.*)?$", servers[0].get("url", ""))
    return (match.group(1) if match else "") or ""


def contract_routes(directory: Path) -> set[Route]:
    """Método e caminho de cada rota descrita nos contratos da pasta."""
    routes = set()
    for contract in sorted(directory.glob("*.yaml")):
        document = yaml.safe_load(contract.read_text(encoding="utf-8"))
        base = _base_path(document).rstrip("/")
        for path, operations in (document.get("paths") or {}).items():
            for method in operations:
                if method.lower() in HTTP_METHODS:
                    routes.add((method.upper(), _normalize(base + path)))
    return routes


def divergences(api: set[Route], contracts: set[Route]) -> tuple[list[Route], list[Route]]:
    """(rotas da API sem contrato, rotas de contrato que a API não tem), já sem as exceções."""
    without_contract = sorted(api - contracts - set(OUTSIDE_CONTRACT), key=lambda r: (r[1], r[0]))
    without_route = sorted(contracts - api, key=lambda r: (r[1], r[0]))
    return without_contract, without_route


def _listing(routes: list[Route]) -> str:
    return "\n".join(f"  {method:6} {path}" for method, path in routes)


def test_there_are_contracts_to_compare() -> None:
    """Guarda contra o gate passar por engano se a pasta mudar de lugar."""
    assert len(list(CONTRACTS_DIR.glob("*.yaml"))) >= 9
    assert len(contract_routes(CONTRACTS_DIR)) >= 40


@pytest.mark.parametrize("contract", sorted(CONTRACTS_DIR.glob("*.yaml")), ids=lambda p: p.name)
def test_contract_is_an_openapi_document(contract: Path) -> None:
    document = yaml.safe_load(contract.read_text(encoding="utf-8"))
    assert str(document.get("openapi", "")).startswith("3."), f"{contract.name}: sem `openapi: 3.x`"
    assert document.get("paths"), f"{contract.name}: sem `paths`"


def test_every_api_route_has_a_contract() -> None:
    without_contract, _ = divergences(api_routes(app), contract_routes(CONTRACTS_DIR))
    assert not without_contract, (
        "rotas da API sem contrato em products/ecommerce/contracts/api/:\n"
        f"{_listing(without_contract)}\n"
        "Descreva a rota no contrato do assunto dela (Contract-First, docs/api/README.md)."
    )


def test_every_contract_route_exists_in_the_api() -> None:
    _, without_route = divergences(api_routes(app), contract_routes(CONTRACTS_DIR))
    assert not without_route, (
        "rotas descritas no contrato que a API não tem:\n"
        f"{_listing(without_route)}\n"
        "A rota mudou de caminho ou saiu? Atualize o contrato no mesmo PR."
    )


def test_every_exception_has_a_reason() -> None:
    for route, reason in OUTSIDE_CONTRACT.items():
        assert reason and len(reason) > 10, f"{route} sem motivo útil"


def test_the_gate_catches_both_directions(tmp_path: Path) -> None:
    """Prova que o teste falharia: sem isto, ele poderia estar sempre verde."""
    sample_app = FastAPI()

    @sample_app.get("/api/sample/{item_id}")
    def read_item(item_id: str) -> dict[str, str]:
        return {"id": item_id}

    @sample_app.post("/api/sample")
    def create_item() -> dict[str, str]:
        return {}

    (tmp_path / "sample.yaml").write_text(
        "openapi: 3.0.3\n"
        "servers:\n"
        "  - url: http://localhost:8000/api/sample\n"
        "paths:\n"
        "  /{id}:\n"
        "    get: {}\n"
        "  /{id}/archive:\n"
        "    post: {}\n",
        encoding="utf-8",
    )

    without_contract, without_route = divergences(api_routes(sample_app), contract_routes(tmp_path))

    assert without_contract == [("POST", "/api/sample")]
    assert without_route == [("POST", "/api/sample/{}/archive")]
