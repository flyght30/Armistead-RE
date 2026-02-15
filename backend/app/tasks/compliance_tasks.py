"""Celery tasks for Phase 7: Brokerage — compliance evaluation and performance snapshots."""
import logging
from datetime import date

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_sync_session():
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db/ttc")
    sync_url = db_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(name="app.tasks.compliance_tasks.evaluate_all_compliance")
def evaluate_all_compliance():
    """Nightly: evaluate compliance rules for all active brokerage transactions."""
    from app.models.brokerage import Brokerage, ComplianceRule
    from app.models import Transaction
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    session = _get_sync_session()
    try:
        # Get all active brokerages
        brokerages = session.execute(
            select(Brokerage).where(Brokerage.is_active == True)
        ).scalars().all()

        total_checks = 0
        for brokerage in brokerages:
            rules = session.execute(
                select(ComplianceRule).where(
                    ComplianceRule.brokerage_id == brokerage.id,
                    ComplianceRule.is_active == True,
                )
            ).scalars().all()

            if not rules:
                continue

            # Get all active transactions for this brokerage's agents
            from app.models.brokerage import BrokerageAgent
            agent_ids = session.execute(
                select(BrokerageAgent.user_id).where(
                    BrokerageAgent.brokerage_id == brokerage.id,
                    BrokerageAgent.is_active == True,
                )
            ).scalars().all()

            if not agent_ids:
                continue

            transactions = session.execute(
                select(Transaction)
                .options(
                    selectinload(Transaction.milestones),
                    selectinload(Transaction.parties),
                    selectinload(Transaction.files),
                    selectinload(Transaction.communications),
                )
                .where(
                    Transaction.agent_id.in_(agent_ids),
                    Transaction.status.in_(["active", "confirmed", "pending_close"]),
                )
            ).scalars().all()

            for txn in transactions:
                for rule in rules:
                    # Check if rule applies to this transaction status
                    applies_to = rule.applies_to_status
                    if applies_to and txn.status not in applies_to:
                        continue

                    passed = _evaluate_rule(txn, rule)
                    _upsert_compliance_check(session, txn.id, rule.id, txn.agent_id, passed, rule.severity)
                    total_checks += 1

        session.commit()
        logger.info(f"Compliance evaluation complete: {total_checks} checks across {len(brokerages)} brokerages")
    except Exception as e:
        session.rollback()
        logger.error(f"Error in compliance evaluation: {e}")
        raise
    finally:
        session.close()


def _evaluate_rule(transaction, rule):
    """Evaluate a single compliance rule against a transaction."""
    params = rule.parameters or {}

    if rule.rule_type == "milestone_deadline":
        max_overdue = params.get("max_overdue_days", 0)
        for m in transaction.milestones:
            if m.status in ("completed", "waived", "cancelled"):
                continue
            if m.due_date:
                days_overdue = (date.today() - m.due_date.date()).days if hasattr(m.due_date, 'date') else 0
                if days_overdue > max_overdue:
                    return False
        return True

    elif rule.rule_type == "required_party":
        required_role = params.get("role")
        if required_role:
            return any(p.role == required_role for p in transaction.parties)
        return True

    elif rule.rule_type == "required_document":
        required_type = params.get("content_type")
        if required_type:
            return any(f.content_type == required_type for f in transaction.files)
        return True

    elif rule.rule_type == "required_communication":
        min_count = params.get("min_count", 1)
        return len(transaction.communications) >= min_count

    elif rule.rule_type == "health_score_min":
        min_score = params.get("min_score", 50)
        return (transaction.health_score or 100) >= min_score

    elif rule.rule_type == "closing_date_required":
        return transaction.closing_date is not None

    return True


def _upsert_compliance_check(session, transaction_id, rule_id, agent_id, passed, severity):
    """Create or update a compliance check record."""
    from app.models.brokerage import ComplianceCheck
    from sqlalchemy import select

    existing = session.execute(
        select(ComplianceCheck).where(
            ComplianceCheck.transaction_id == transaction_id,
            ComplianceCheck.rule_id == rule_id,
        )
    ).scalar_one_or_none()

    status = "pass" if passed else ("warning" if severity == "warning" else "fail")

    if existing:
        if existing.status != "overridden":
            existing.status = status
            existing.checked_at = date.today()
    else:
        check = ComplianceCheck(
            transaction_id=transaction_id,
            rule_id=rule_id,
            agent_id=agent_id,
            status=status,
        )
        session.add(check)


@celery_app.task(name="app.tasks.compliance_tasks.compute_performance_snapshots")
def compute_performance_snapshots():
    """Nightly: compute agent performance snapshots for all brokerages."""
    from app.models.brokerage import Brokerage, BrokerageAgent, AgentPerformanceSnapshot
    from app.models import Transaction
    from sqlalchemy import select, func
    from datetime import datetime

    session = _get_sync_session()
    try:
        today = date.today()
        year_start = date(today.year, 1, 1)
        month_start = date(today.year, today.month, 1)

        brokerages = session.execute(
            select(Brokerage).where(Brokerage.is_active == True)
        ).scalars().all()

        for brokerage in brokerages:
            agents = session.execute(
                select(BrokerageAgent).where(
                    BrokerageAgent.brokerage_id == brokerage.id,
                    BrokerageAgent.is_active == True,
                )
            ).scalars().all()

            for ba in agents:
                # Check if snapshot already exists for today
                existing = session.execute(
                    select(AgentPerformanceSnapshot).where(
                        AgentPerformanceSnapshot.agent_id == ba.user_id,
                        AgentPerformanceSnapshot.snapshot_date == today,
                    )
                ).scalar_one_or_none()

                # Count transactions
                active_deals = session.execute(
                    select(func.count(Transaction.id)).where(
                        Transaction.agent_id == ba.user_id,
                        Transaction.status.in_(["active", "confirmed", "pending_close"]),
                    )
                ).scalar() or 0

                closed_ytd = session.execute(
                    select(func.count(Transaction.id)).where(
                        Transaction.agent_id == ba.user_id,
                        Transaction.status == "closed",
                        Transaction.updated_at >= year_start,
                    )
                ).scalar() or 0

                closed_mtd = session.execute(
                    select(func.count(Transaction.id)).where(
                        Transaction.agent_id == ba.user_id,
                        Transaction.status == "closed",
                        Transaction.updated_at >= month_start,
                    )
                ).scalar() or 0

                lost_ytd = session.execute(
                    select(func.count(Transaction.id)).where(
                        Transaction.agent_id == ba.user_id,
                        Transaction.status.in_(["cancelled", "deleted"]),
                        Transaction.updated_at >= year_start,
                    )
                ).scalar() or 0

                if existing:
                    existing.active_deals = active_deals
                    existing.closed_ytd = closed_ytd
                    existing.closed_mtd = closed_mtd
                    existing.lost_ytd = lost_ytd
                else:
                    snapshot = AgentPerformanceSnapshot(
                        agent_id=ba.user_id,
                        brokerage_id=brokerage.id,
                        snapshot_date=today,
                        active_deals=active_deals,
                        closed_ytd=closed_ytd,
                        closed_mtd=closed_mtd,
                        lost_ytd=lost_ytd,
                    )
                    session.add(snapshot)

        session.commit()
        logger.info(f"Performance snapshots computed for {len(brokerages)} brokerages")
    except Exception as e:
        session.rollback()
        logger.error(f"Error computing performance snapshots: {e}")
        raise
    finally:
        session.close()
