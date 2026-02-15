from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.services import email_delivery_service

router = APIRouter()


@router.post("/webhooks/resend")
async def resend_webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Handle Resend webhook events for email delivery tracking."""
    body = await request.json()
    event_type = body.get("type", "")
    data = body.get("data", {})

    await email_delivery_service.process_webhook(event_type, data, db)
    return {"received": True}


@router.get("/unsubscribe/{token}")
async def unsubscribe(
    token: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Handle email unsubscribe via token."""
    success = await email_delivery_service.handle_unsubscribe(token, db)
    if not success:
        raise HTTPException(status_code=404, detail="Invalid unsubscribe link")
    return {"success": True, "message": "You have been unsubscribed from notifications."}
