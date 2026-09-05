"""Ponto de entrada FastAPI do api-gateway.

Composição: monta os routers de cada core que já expõe API HTTP. Hoje
core-catalog, core-cart e core-inventory; os demais cores entram aqui
conforme forem implementados.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_gateway.routers.cart import router as cart_router
from api_gateway.routers.catalog import router as catalog_router
from api_gateway.routers.inventory import router as inventory_router

app = FastAPI(
    title="Revold API Gateway",
    description="Composição das APIs HTTP dos cores do monorepo revold.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog_router)
app.include_router(cart_router)
app.include_router(inventory_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
