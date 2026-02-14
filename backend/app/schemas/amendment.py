from datetime import datetime
from typing import Any, Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class AmendmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    field_changed: str
    old_value: Dict[str, Any]
    new_value: Dict[str, Any]
    reason: str
    changed_by_id: UUID
    notification_sent: bool
    created_at: datetime
    updated_at: datetime
