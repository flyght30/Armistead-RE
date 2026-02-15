"""Celery tasks for Phase 2: Nudge Engine — milestone reminders, email sending, draft expiration."""
import logging
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_sync_session():
    """Create a synchronous database session for Celery tasks."""
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db/ttc")
    # Celery needs sync driver
    sync_url = db_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(name="app.tasks.notification_tasks.check_milestone_reminders")
def check_milestone_reminders():
    """Hourly: check all active transactions for milestone reminders and escalations."""
    from app.models import User, Transaction, Milestone, Party, NotificationRule
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    session = _get_sync_session()
    try:
        # Get all agents with active transactions and vacation_mode off
        stmt = (
            select(User)
            .join(Transaction, Transaction.agent_id == User.id)
            .where(Transaction.status.in_(["active", "confirmed", "pending_close"]))
            .distinct()
        )
        agents = session.execute(stmt).scalars().all()

        for agent in agents:
            prefs = agent.notification_preferences or {}
            if prefs.get("vacation_mode", False):
                continue

            tz_name = prefs.get("timezone", "America/New_York")
            try:
                agent_tz = ZoneInfo(tz_name)
            except Exception:
                agent_tz = ZoneInfo("America/New_York")

            agent_today = datetime.now(agent_tz).date()

            # Get agent's notification rules
            rules_stmt = select(NotificationRule).where(
                NotificationRule.agent_id == agent.id,
                NotificationRule.is_active == True,
            )
            rules = session.execute(rules_stmt).scalars().all()
            rules_by_type = {r.milestone_type: r for r in rules}

            # Get all active transactions for this agent
            txn_stmt = (
                select(Transaction)
                .options(
                    selectinload(Transaction.milestones),
                    selectinload(Transaction.parties),
                )
                .where(
                    Transaction.agent_id == agent.id,
                    Transaction.status.in_(["active", "confirmed", "pending_close"]),
                )
            )
            transactions = session.execute(txn_stmt).scalars().all()

            for txn in transactions:
                overrides = txn.notification_overrides or {}
                if not overrides.get("reminders_enabled", True):
                    continue

                for milestone in txn.milestones:
                    if milestone.status in ("completed", "waived", "cancelled"):
                        continue
                    if not milestone.due_date:
                        continue

                    # Check if reminders paused
                    if milestone.reminders_paused_until and milestone.reminders_paused_until > datetime.now(agent_tz):
                        continue

                    due_date = milestone.due_date.date() if hasattr(milestone.due_date, 'date') else milestone.due_date
                    days_until = (due_date - agent_today).days

                    # Find matching rule
                    rule = rules_by_type.get(milestone.type) or rules_by_type.get("*")
                    if not rule:
                        continue

                    reminder_days = overrides.get("reminder_days_override") or rule.days_before

                    if days_until > 0 and days_until <= reminder_days:
                        _create_reminder_notification(
                            session, txn, milestone, agent, rule, "reminder", 0
                        )
                    elif days_until == 0:
                        _create_reminder_notification(
                            session, txn, milestone, agent, rule, "due_today", 0
                        )
                    elif days_until < 0:
                        days_overdue = abs(days_until)
                        escalation_days = rule.escalation_days or [1, 3, 7]
                        if rule.escalation_enabled:
                            level = 0
                            for i, threshold in enumerate(escalation_days):
                                if days_overdue >= threshold:
                                    level = i + 1
                            notification_type = f"overdue_l{min(level, 3)}"
                            _create_reminder_notification(
                                session, txn, milestone, agent, rule,
                                notification_type, min(level, 3)
                            )

        session.commit()
        logger.info("Milestone reminder check completed")
    except Exception as e:
        session.rollback()
        logger.error(f"Error checking milestone reminders: {e}")
        raise
    finally:
        session.close()


def _create_reminder_notification(session, transaction, milestone, agent, rule, notification_type, escalation_level):
    """Create a notification log entry or email draft for a milestone reminder."""
    from app.models import NotificationLog, Party

    today_str = date.today().isoformat()

    # Get responsible party
    responsible_parties = [
        p for p in transaction.parties
        if p.role == milestone.responsible_party_role
    ]
    if not responsible_parties:
        return

    for party in responsible_parties:
        if not party.email:
            continue
        if party.email_bounced or party.unsubscribed_at:
            continue
        if party.notification_preference == "none":
            continue

        # Check idempotency
        idempotency_key = f"{milestone.id}:{party.email}:{notification_type}:{today_str}"
        from sqlalchemy import select
        existing = session.execute(
            select(NotificationLog).where(NotificationLog.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing:
            continue

        # Create notification log entry
        log_entry = NotificationLog(
            transaction_id=transaction.id,
            milestone_id=milestone.id,
            rule_id=rule.id,
            type=notification_type,
            escalation_level=escalation_level,
            recipient_email=party.email,
            recipient_name=party.name,
            recipient_role=party.role,
            subject=f"Reminder: {milestone.title}",
            status="queued",
            scheduled_for=datetime.utcnow(),
            idempotency_key=idempotency_key,
        )
        session.add(log_entry)

        # Update milestone tracking
        milestone.reminder_sent_count = (milestone.reminder_sent_count or 0) + 1
        milestone.escalation_level = escalation_level


@celery_app.task(name="app.tasks.notification_tasks.send_queued_emails")
def send_queued_emails():
    """Every 5 min: send queued notification emails via Resend."""
    from app.models import NotificationLog, Communication, Milestone
    from sqlalchemy import select
    import os

    resend_api_key = os.getenv("RESEND_API_KEY", "")
    if not resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping email send")
        return

    session = _get_sync_session()
    try:
        now = datetime.utcnow()
        stmt = (
            select(NotificationLog)
            .where(
                NotificationLog.status == "queued",
                NotificationLog.scheduled_for <= now,
            )
            .order_by(
                NotificationLog.escalation_level.desc(),
                NotificationLog.scheduled_for.asc(),
            )
            .limit(50)
        )
        notifications = session.execute(stmt).scalars().all()

        for notif in notifications:
            # Pre-send validation: check if milestone was completed
            if notif.milestone_id:
                milestone = session.get(Milestone, notif.milestone_id)
                if milestone and milestone.status in ("completed", "waived", "cancelled"):
                    notif.status = "cancelled"
                    notif.error_message = "Milestone completed before send"
                    continue

            try:
                import resend as resend_lib
                resend_lib.api_key = resend_api_key
                result = resend_lib.Emails.send({
                    "from": os.getenv("RESEND_FROM_EMAIL", "noreply@armistead.re"),
                    "to": [notif.recipient_email],
                    "subject": notif.subject or "Transaction Update",
                    "html": f"<p>{notif.subject}</p>",
                })
                notif.status = "sent"
                notif.sent_at = datetime.utcnow()
                notif.resend_message_id = result.get("id") if isinstance(result, dict) else str(result)

                # Create communication record
                comm = Communication(
                    transaction_id=notif.transaction_id,
                    milestone_id=notif.milestone_id,
                    type="email",
                    recipient_email=notif.recipient_email,
                    subject=notif.subject or "",
                    body=notif.subject or "",
                    status="sent",
                    delivery_status="sent",
                    sent_at=datetime.utcnow(),
                    notification_log_id=notif.id,
                )
                session.add(comm)
                notif.communication_id = comm.id

            except Exception as e:
                notif.retry_count = (notif.retry_count or 0) + 1
                if notif.retry_count >= 5:
                    notif.status = "failed"
                    notif.error_message = str(e)
                else:
                    # Exponential backoff: 30s, 2m, 8m, 30m, 2h
                    backoff_seconds = [30, 120, 480, 1800, 7200]
                    delay = backoff_seconds[min(notif.retry_count - 1, 4)]
                    notif.scheduled_for = datetime.utcnow() + timedelta(seconds=delay)
                    notif.error_message = str(e)
                logger.error(f"Failed to send email to {notif.recipient_email}: {e}")

        session.commit()
        logger.info(f"Processed {len(notifications)} queued emails")
    except Exception as e:
        session.rollback()
        logger.error(f"Error sending queued emails: {e}")
        raise
    finally:
        session.close()


@celery_app.task(name="app.tasks.notification_tasks.expire_stale_drafts")
def expire_stale_drafts():
    """Daily: expire email drafts older than 48 hours."""
    from app.models import EmailDraft
    from sqlalchemy import select, update

    session = _get_sync_session()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=48)
        stmt = (
            update(EmailDraft)
            .where(
                EmailDraft.status == "draft",
                EmailDraft.created_at < cutoff,
            )
            .values(status="expired")
        )
        result = session.execute(stmt)
        session.commit()
        logger.info(f"Expired {result.rowcount} stale email drafts")
    except Exception as e:
        session.rollback()
        logger.error(f"Error expiring stale drafts: {e}")
        raise
    finally:
        session.close()
