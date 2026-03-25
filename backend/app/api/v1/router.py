from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.qa import router as qa_router
from app.api.v1.rates import router as rates_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(qa_router, tags=["qa"])
router.include_router(rates_router, tags=["rates"])
