from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.commission import (
    CommissionConfigCreate, CommissionConfigUpdate, CommissionConfigResponse,
    TransactionCommissionCreate, TransactionCommissionUpdate, TransactionCommissionResponse,
    PipelineSummary, CSVExportRequest,
)
from app.services import commission_service

router = APIRouter()

DEV_AGENT_ID = "00000000-0000-0000-0000-000000000001"


# --- Commission Config ---

@router.get("/commission-config", response_model=CommissionConfigResponse)
async def get_commission_config(
    db: AsyncSession = Depends(get_async_session),
):
    agent_id = UUID(DEV_AGENT_ID)
    config = await commission_service.get_config(agent_id, db)
    if not config:
        return CommissionConfigResponse(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            agent_id=agent_id,
            commission_type="percentage",
            created_at=None,
            updated_at=None,
        )
    return config


@router.put("/commission-config", response_model=CommissionConfigResponse)
async def upsert_commission_config(
    config_data: CommissionConfigCreate,
    db: AsyncSession = Depends(get_async_session),
):
    agent_id = UUID(DEV_AGENT_ID)
    return await commission_service.upsert_config(agent_id, config_data, db)


# --- Transaction Commission ---

@router.get("/transactions/{transaction_id}/commission", response_model=TransactionCommissionResponse)
async def get_transaction_commission(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    commission = await commission_service.get_transaction_commission(transaction_id, db)
    if not commission:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No commission found for this transaction")
    return commission


@router.post("/transactions/{transaction_id}/commission", response_model=TransactionCommissionResponse)
async def create_transaction_commission(
    transaction_id: UUID,
    commission_data: TransactionCommissionCreate,
    db: AsyncSession = Depends(get_async_session),
):
    agent_id = UUID(DEV_AGENT_ID)
    return await commission_service.create_transaction_commission(
        transaction_id, agent_id, commission_data, db
    )


@router.patch("/transactions/{transaction_id}/commission", response_model=TransactionCommissionResponse)
async def update_transaction_commission(
    transaction_id: UUID,
    commission_update: TransactionCommissionUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    return await commission_service.update_transaction_commission(
        transaction_id, commission_update, db
    )


# --- Pipeline ---

@router.get("/pipeline", response_model=PipelineSummary)
async def get_pipeline(
    db: AsyncSession = Depends(get_async_session),
):
    agent_id = UUID(DEV_AGENT_ID)
    return await commission_service.get_pipeline_summary(agent_id, db)


@router.get("/pipeline/export")
async def export_pipeline_csv(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    agent_id = UUID(DEV_AGENT_ID)
    csv_data = await commission_service.export_csv(agent_id, db, status=status)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pipeline_export.csv"},
    )
