from __future__ import annotations

from fastapi import APIRouter

from patchbay_gateway.api.v1 import chat, keys, mcp, models, models_sync, usage, seed

router = APIRouter()

router.include_router(chat.router, tags=["chat"])
router.include_router(models.router, tags=["models"])
router.include_router(models_sync.router, tags=["models-sync"])
router.include_router(keys.router, tags=["keys"])
router.include_router(usage.router, tags=["usage"])
router.include_router(mcp.router, tags=["mcp"])
router.include_router(seed.router, tags=["seed"])
