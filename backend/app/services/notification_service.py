import logging
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification_rule import NotificationRule
from app.models.notification_log import NotificationLog
from app.models.email_draft import EmailDraft
from app.models.user import User
from app.schemas.notification import (
    NotificationRuleCreate, NotificationRuleUpdate, NotificationRuleResponse,
    NotificationLogResponse, NotificationSettingsUpdate,
)

logger = logging.getLogger(__name__)


async def list_rules(
    agent_id: UUID, db: AsyncSession
) -> List[NotificationRuleResponse]:
    stmt = select(NotificationRule).where(NotificationRule.agent_id == agent_id)
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [NotificationRuleResponse.model_validate(r) for r in rules]


async def create_rule(
    agent_id: UUID, rule_create: NotificationRuleCreate, db: AsyncSession
) -> NotificationRuleResponse:
    rule = NotificationRule(agent_id=agent_id, **rule_create.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return NotificationRuleResponse.model_validate(rule)


async def update_rule(
    rule_id: UUID, rule_update: NotificationRuleUpdate, db: AsyncSession
) -> NotificationRuleResponse:
    rule = await db.get(NotificationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Notification rule not found")
    for field, value in rule_update.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return NotificationRuleResponse.model_validate(rule)


async def delete_rule(rule_id: UUID, db: AsyncSession) -> None:
    rule = await db.get(NotificationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Notification rule not found")
    await db.delete(rule)
    await db.commit()


async def list_logs(
    transaction_id: UUID, db: AsyncSession, status: Optional[str] = None
) -> List[NotificationLogResponse]:
    stmt = select(NotificationLog).where(
        NotificationLog.transaction_id == transaction_id
    )
    if status:
        stmt = stmt.where(NotificationLog.status == status)
    stmt = stmt.order_by(NotificationLog.created_at.desc())
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [NotificationLogResponse.model_validate(log) for log in logs]


async def update_notification_settings(
    agent_id: UUID, settings: NotificationSettingsUpdate, db: AsyncSession
) -> dict:
    user = await db.get(User, agent_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = settings.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return {
        "notification_preferences": user.notification_preferences,
        "timezone": user.timezone,
    }
