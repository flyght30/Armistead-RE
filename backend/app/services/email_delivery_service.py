import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification_log import NotificationLog
from app.models.communication import Communication
from app.config import Settings

logger = logging.getLogger(__name__)

settings = Settings()


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    from_email: Optional[str] = None,
) -> dict:
    """Send an email via Resend API. Returns {id, status}."""
    try:
        import resend
        resend.api_key = settings.resend_api_key

        if not settings.resend_api_key:
            logger.warning("Resend API key not set, skipping email send")
            return {"id": None, "status": "skipped"}

        email_params = {
            "from": from_email or settings.resend_from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        result = resend.Emails.send(email_params)
        return {"id": result.get("id"), "status": "sent"}
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return {"id": None, "status": "failed", "error": str(e)}


async def process_webhook(
    event_type: str, data: dict, db: AsyncSession
) -> None:
    """Process a Resend webhook event and update notification log."""
    message_id = data.get("email_id")
    if not message_id:
        return

    stmt = select(NotificationLog).where(
        NotificationLog.resend_message_id == message_id
    )
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()
    if not log:
        logger.warning(f"No notification log found for message_id={message_id}")
        return

    now = datetime.now(timezone.utc)
    if event_type == "email.delivered":
        log.delivered_at = now
        log.status = "delivered"
    elif event_type == "email.opened":
        log.opened_at = now
    elif event_type == "email.clicked":
        log.clicked_at = now
    elif event_type == "email.bounced":
        log.bounced_at = now
        log.bounce_reason = data.get("bounce", {}).get("message", "Unknown")
        log.status = "bounced"
    elif event_type == "email.complained":
        log.status = "complained"

    await db.commit()


async def handle_unsubscribe(token: str, db: AsyncSession) -> bool:
    """Handle unsubscribe via token. Returns True if successful."""
    from app.models.party import Party

    stmt = select(Party).where(Party.unsubscribe_token == token)
    result = await db.execute(stmt)
    party = result.scalar_one_or_none()
    if not party:
        return False

    party.unsubscribed_at = datetime.now(timezone.utc)
    await db.commit()
    return True
