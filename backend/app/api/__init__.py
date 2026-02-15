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

# Phase 2: Nudge Engine
from .notifications import router as notifications_router
from .email_drafts import router as email_drafts_router
from .webhooks import router as webhooks_router

# Phase 3: Party Portal
from .portal import router as portal_router

# Phase 4: AI Advisor
from .advisor import router as advisor_router

# Phase 5: Money
from .commissions import router as commissions_router

# Phase 6: Docs Generation
from .documents import router as documents_router

# Phase 7: Brokerage
from .brokerage import router as brokerage_router

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

# New phase routers
router.include_router(notifications_router, tags=["notifications"])
router.include_router(email_drafts_router, tags=["email-drafts"])
router.include_router(webhooks_router, tags=["webhooks"])
router.include_router(portal_router, tags=["portal"])
router.include_router(advisor_router, tags=["advisor"])
router.include_router(commissions_router, tags=["commissions"])
router.include_router(documents_router, tags=["documents"])
router.include_router(brokerage_router, tags=["brokerage"])
