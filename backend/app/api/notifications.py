from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.auth import get_current_agent_id
from app.schemas.notification import (
    NotificationRuleCreate, NotificationRuleUpdate, NotificationRuleResponse,
    NotificationLogResponse, NotificationSettingsUpdate,
)
from app.services import notification_service

router = APIRouter()


@router.get("/notification-rules", response_model=List[NotificationRuleResponse])
async def list_notification_rules(
    db: AsyncSession = Depends(get_async_session),
    agent_id: UUID = Depends(get_current_agent_id),
):
    return await notification_service.list_rules(agent_id, db)


@router.post("/notification-rules", response_model=NotificationRuleResponse)
async def create_notification_rule(
    rule_create: NotificationRuleCreate,
    db: AsyncSession = Depends(get_async_session),
    agent_id: UUID = Depends(get_current_agent_id),
):
    return await notification_service.create_rule(agent_id, rule_create, db)


@router.patch("/notification-rules/{rule_id}", response_model=NotificationRuleResponse)
async def update_notification_rule(
    rule_id: UUID,
    rule_update: NotificationRuleUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    return await notification_service.update_rule(rule_id, rule_update, db)


@router.delete("/notification-rules/{rule_id}")
async def delete_notification_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    await notification_service.delete_rule(rule_id, db)
    return {"success": True}


@router.get("/transactions/{transaction_id}/notification-logs", response_model=List[NotificationLogResponse])
async def list_notification_logs(
    transaction_id: UUID,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    return await notification_service.list_logs(transaction_id, db, status=status)


@router.put("/notification-settings", response_model=dict)
async def update_notification_settings(
    settings: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_async_session),
    agent_id: UUID = Depends(get_current_agent_id),
):
    return await notification_service.update_notification_settings(agent_id, settings, db)
