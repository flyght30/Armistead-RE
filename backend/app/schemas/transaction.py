from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from .common import PaginationParams

class TransactionBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str
    created_by_id: UUID
    updated_by_id: UUID

class TransactionCreate(TransactionBase):
    file_path: str

class TransactionUpdate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    parties: List['PartyResponse']

class TransactionList(BaseModel):
    items: List[TransactionResponse]
    pagination: PaginationParams
