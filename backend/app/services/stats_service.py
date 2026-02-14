from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction


async def get_dashboard_stats(db: AsyncSession):
    # Total non-deleted
    total_stmt = select(func.count()).select_from(Transaction).where(Transaction.status != "deleted")
    total = (await db.execute(total_stmt)).scalar() or 0

    # By status
    status_stmt = (
        select(Transaction.status, func.count())
        .where(Transaction.status != "deleted")
        .group_by(Transaction.status)
    )
    result = await db.execute(status_stmt)
    status_counts = {row[0]: row[1] for row in result.all()}

    # Closing this month
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        month_end = month_start.replace(year=now.year + 1, month=1)
    else:
        month_end = month_start.replace(month=now.month + 1)

    closing_stmt = (
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.status != "deleted",
            Transaction.closing_date >= month_start,
            Transaction.closing_date < month_end,
        )
    )
    closing_this_month = (await db.execute(closing_stmt)).scalar() or 0

    return {
        "total": total,
        "draft": status_counts.get("draft", 0),
        "pending_review": status_counts.get("pending_review", 0),
        "confirmed": status_counts.get("confirmed", 0),
        "closing_this_month": closing_this_month,
    }
