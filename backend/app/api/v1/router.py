from fastapi import APIRouter

from app.api.v1.routes.jobs import router as jobs_router
from app.api.v1.routes.recipes import router as recipes_router

router = APIRouter(prefix="/api/v1")
router.include_router(jobs_router)
router.include_router(recipes_router)
