import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.action_item import ActionItem
from app.models.milestone import Milestone
from app.models.transaction import Transaction
from app.schemas.action_item import ActionItemResponse, TodayViewResponse

logger = logging.getLogger(__name__)


async def get_today_view(
    agent_id: UUID,
    db: AsyncSession,
    transaction_id: Optional[UUID] = None,
    priority: Optional[str] = None,
    filter_section: Optional[str] = None,
) -> TodayViewResponse:
    """Build the Today View: aggregate action items across all active transactions."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    three_days = today_start + timedelta(days=4)  # end of "coming up" (3 days from tomorrow)
    seven_days = today_start + timedelta(days=8)  # end of "this week"

    # First, auto-generate action items from milestones
    await _auto_generate_action_items(agent_id, db)

    # Query action items
    stmt = (
        select(ActionItem)
        .join(Transaction, ActionItem.transaction_id == Transaction.id)
        .where(
            Transaction.agent_id == agent_id,
            Transaction.status.notin_(["draft", "deleted", "closed"]),
            ActionItem.status == "pending",
        )
    )

    if transaction_id:
        stmt = stmt.where(ActionItem.transaction_id == transaction_id)
    if priority:
        stmt = stmt.where(ActionItem.priority == priority)

    result = await db.execute(stmt)
    items = result.scalars().all()

    # Categorize into sections
    overdue = []
    due_today = []
    coming_up = []
    this_week = []

    for item in items:
        resp = ActionItemResponse.model_validate(item)
        if item.due_date is None:
            # Items without dates go to "this_week" as low priority
            this_week.append(resp)
        elif item.due_date < today_start:
            overdue.append(resp)
        elif item.due_date < today_end:
            due_today.append(resp)
        elif item.due_date < three_days:
            coming_up.append(resp)
        elif item.due_date < seven_days:
            this_week.append(resp)
        # Items beyond 7 days are not shown in Today View

    # Sort each section by priority then due_date
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for section in [overdue, due_today, coming_up, this_week]:
        section.sort(key=lambda x: (
            priority_order.get(x.priority, 2),
            x.due_date or datetime.max.replace(tzinfo=timezone.utc),
        ))

    return TodayViewResponse(
        overdue=overdue,
        due_today=due_today,
        coming_up=coming_up,
        this_week=this_week,
        summary={
            "overdue_count": len(overdue),
            "due_today_count": len(due_today),
            "coming_up_count": len(coming_up),
            "this_week_count": len(this_week),
        },
    )


async def _auto_generate_action_items(agent_id: UUID, db: AsyncSession):
    """Auto-generate action items from milestone analysis."""
    now = datetime.now(timezone.utc)

    # Get all active transactions for this agent
    txn_stmt = (
        select(Transaction)
        .where(
            Transaction.agent_id == agent_id,
            Transaction.status.notin_(["draft", "deleted", "closed"]),
        )
        .options(
            selectinload(Transaction.milestones),
            selectinload(Transaction.action_items),
            selectinload(Transaction.parties),
            selectinload(Transaction.files),
        )
    )
    result = await db.execute(txn_stmt)
    transactions = result.scalars().all()

    for txn in transactions:
        existing_item_keys = {
            (ai.type, ai.milestone_id): ai
            for ai in txn.action_items
            if ai.status not in ("completed", "dismissed")
        }

        for milestone in txn.milestones:
            if milestone.status in ("completed", "pending_date"):
                continue

            if milestone.due_date is None:
                continue

            # Overdue milestone
            if milestone.due_date < now and milestone.status != "completed":
                key = ("milestone_overdue", milestone.id)
                if key not in existing_item_keys:
                    days_overdue = (now - milestone.due_date).days
                    item = ActionItem(
                        transaction_id=txn.id,
                        milestone_id=milestone.id,
                        type="milestone_overdue",
                        title=f"OVERDUE: {milestone.title} ({days_overdue}d late)",
                        description=f"This milestone for {txn.property_address or 'Unknown Property'} is {days_overdue} days overdue.",
                        priority="critical" if days_overdue > 3 else "high",
                        due_date=milestone.due_date,
                        agent_id=agent_id,
                    )
                    db.add(item)

            # Upcoming milestone (within reminder window)
            elif milestone.due_date >= now:
                reminder_days = milestone.reminder_days_before or 2
                reminder_start = milestone.due_date - timedelta(days=reminder_days)
                if now >= reminder_start:
                    key = ("milestone_due", milestone.id)
                    if key not in existing_item_keys:
                        days_until = (milestone.due_date - now).days
                        if days_until == 0:
                            priority = "high"
                            title = f"DUE TODAY: {milestone.title}"
                        elif days_until <= 1:
                            priority = "high"
                            title = f"DUE TOMORROW: {milestone.title}"
                        else:
                            priority = "medium"
                            title = f"Due in {days_until}d: {milestone.title}"

                        item = ActionItem(
                            transaction_id=txn.id,
                            milestone_id=milestone.id,
                            type="milestone_due",
                            title=title,
                            description=f"Milestone for {txn.property_address or 'Unknown Property'}. Responsible: {milestone.responsible_party_role}.",
                            priority=priority,
                            due_date=milestone.due_date,
                            agent_id=agent_id,
                        )
                        db.add(item)

        # Missing party checks
        party_roles = {p.role.lower() for p in txn.parties}
        if "buyer" not in party_roles and "buyer_agent" not in party_roles:
            key = ("missing_party", None)
            # Check by type since there's no milestone_id
            has_existing = any(
                ai.type == "missing_party" and "buyer" in ai.title.lower()
                for ai in txn.action_items
                if ai.status not in ("completed", "dismissed")
            )
            if not has_existing:
                item = ActionItem(
                    transaction_id=txn.id,
                    type="missing_party",
                    title=f"Missing buyer/buyer agent on {txn.property_address or 'transaction'}",
                    priority="high",
                    agent_id=agent_id,
                )
                db.add(item)

        if "seller" not in party_roles and "seller_agent" not in party_roles:
            has_existing = any(
                ai.type == "missing_party" and "seller" in ai.title.lower()
                for ai in txn.action_items
                if ai.status not in ("completed", "dismissed")
            )
            if not has_existing:
                item = ActionItem(
                    transaction_id=txn.id,
                    type="missing_party",
                    title=f"Missing seller/seller agent on {txn.property_address or 'transaction'}",
                    priority="high",
                    agent_id=agent_id,
                )
                db.add(item)

        # Closing approaching
        if txn.closing_date:
            days_to_close = (txn.closing_date - now).days
            if 0 <= days_to_close <= 7:
                has_existing = any(
                    ai.type == "closing_approaching"
                    for ai in txn.action_items
                    if ai.status not in ("completed", "dismissed")
                )
                if not has_existing:
                    priority = "critical" if days_to_close <= 2 else "high"
                    item = ActionItem(
                        transaction_id=txn.id,
                        type="closing_approaching",
                        title=f"Closing in {days_to_close}d: {txn.property_address or 'transaction'}",
                        description=f"Closing date: {txn.closing_date.strftime('%b %d, %Y')}",
                        priority=priority,
                        due_date=txn.closing_date,
                        agent_id=agent_id,
                    )
                    db.add(item)

    await db.commit()
