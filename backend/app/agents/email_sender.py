import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


async def send_email(
    recipient_email: str,
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Send an email notification.

    TODO: Integrate with a real email provider (Resend, SendGrid, SES, etc.)
    For now, this logs the email and returns a stub response.
    """
    logger.info(
        "Sending email to=%s subject=%s body_length=%d",
        recipient_email,
        subject,
        len(body),
    )

    # TODO: Replace with actual email sending logic
    # Example with Resend:
    #   import resend
    #   resend.api_key = settings.resend_api_key
    #   result = resend.Emails.send({
    #       "from": "noreply@armistead.com",
    #       "to": recipient_email,
    #       "subject": subject,
    #       "html": body,
    #   })

    return {
        "status": "sent",
        "recipient": recipient_email,
        "subject": subject,
    }
