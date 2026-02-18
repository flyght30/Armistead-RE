from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime


class PartyBase(BaseModel):
    name: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    is_primary: bool = False


class PartyCreate(PartyBase):
    pass


class PartyUpdate(BaseModel):
    """All fields optional for partial updates."""
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    is_primary: Optional[bool] = None


class PartyResponse(PartyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    notes: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
