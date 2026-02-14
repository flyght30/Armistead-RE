from fastapi import APIRouter
from .transactions import router as transactions_router
from .parties import router as parties_router
from .milestones import router as milestones_router
from .amendments import router as amendments_router
from .files import router as files_router
from .inspections import router as inspections_router
from .stats import router as stats_router
from .today import router as today_router
from .templates import router as templates_router
from .action_items import router as action_items_router

router = APIRouter(prefix="/api")
router.include_router(transactions_router, tags=["transactions"])
router.include_router(parties_router, tags=["parties"])
router.include_router(milestones_router, tags=["milestones"])
router.include_router(amendments_router, tags=["amendments"])
router.include_router(files_router, tags=["files"])
router.include_router(inspections_router, tags=["inspections"])
router.include_router(stats_router, tags=["stats"])
router.include_router(today_router, tags=["today"])
router.include_router(templates_router, tags=["templates"])
router.include_router(action_items_router, tags=["action-items"])
