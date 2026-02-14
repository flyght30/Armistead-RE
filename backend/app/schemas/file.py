from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    content_type: str
    url: str
    transaction_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
