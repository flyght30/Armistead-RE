from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from .common import PaginationParams

class PartyBase(BaseModel):
    name: str
    role: str
    contact_info: Optional[str] = None

class PartyCreate(PartyBase):
    transaction_id: UUID

class PartyUpdate(PartyBase):
    pass

class PartyResponse(PartyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
