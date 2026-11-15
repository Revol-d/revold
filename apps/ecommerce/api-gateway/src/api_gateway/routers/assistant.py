"""Router HTTP do `ai-assistant` (ADR-0011).

`ask` é público (widget de chat do storefront). `reindex` é administrativo
(RBAC STAFF/ADMIN) e roda a mesma função de reindexação usada pela tarefa
Celery de apps/ecommerce/catalog-indexer — só sem depender de um worker no ar.
"""
from __future__ import annotations

from revold_ecommerce.application.catalog_indexing import reindex_all_products
from fastapi import APIRouter, Depends

from api_gateway.dependencies import (
    get_llm_provider,
    get_product_index,
    get_product_repository,
)
from api_gateway.security import require_any_role
from revold_ai_assistant.domain import AssistantReply, ChatMessage, Role
from revold_ai_assistant.ports import LLMProvider, ProductIndex
from revold_ai_assistant.application.schemas import (
    AskAssistantRequestSchema,
    AssistantReplySchema,
    ReindexResultSchema,
    RetrievedProductSchema,
)
from revold_ai_assistant.application.use_cases import AskAssistant, IndexProduct
from revold_catalog.ports import ProductRepository
from revold_identity.domain import AuthenticatedUser, Role as UserRole

router = APIRouter(prefix="/api/assistant", tags=["ai-assistant"])


def _reply_to_schema(reply: AssistantReply) -> AssistantReplySchema:
    return AssistantReplySchema(
        message=reply.message,
        escalate_to_whatsapp=reply.escalate_to_whatsapp,
        retrieved_products=[
            RetrievedProductSchema(sku=p.sku, name=p.name) for p in reply.retrieved_products
        ],
    )


@router.post("/ask", response_model=AssistantReplySchema)
async def ask(
    body: AskAssistantRequestSchema,
    llm: LLMProvider = Depends(get_llm_provider),
    index: ProductIndex = Depends(get_product_index),
) -> AssistantReplySchema:
    history = [ChatMessage(role=Role(m.role), content=m.content) for m in body.history]
    reply = await AskAssistant(llm, index).execute(history=history, question=body.question)
    return _reply_to_schema(reply)


@router.post("/reindex", response_model=ReindexResultSchema)
async def reindex(
    llm: LLMProvider = Depends(get_llm_provider),
    index: ProductIndex = Depends(get_product_index),
    product_repository: ProductRepository = Depends(get_product_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> ReindexResultSchema:
    index_product = IndexProduct(llm, index)
    count = await reindex_all_products(product_repository, index_product)
    return ReindexResultSchema(products_indexed=count)
