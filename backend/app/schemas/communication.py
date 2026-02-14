from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CommunicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    milestone_id: Optional[UUID] = None
    recipient_party_id: Optional[UUID] = None
    type: str  # email, sms
    recipient_email: str
    subject: str
    body: str
    attachments: Optional[Dict[str, Any]] = None
    status: str  # pending, sent, opened, clicked, bounced
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    template_used: Optional[str] = None
    created_at: datetime
    updated_at: datetime
