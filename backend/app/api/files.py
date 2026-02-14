from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models.file import File as FileModel
from app.schemas.file import FileResponse
from app.services.storage_service import upload_file, get_file_url

router = APIRouter()


@router.get("/transactions/{transaction_id}/files", response_model=List[FileResponse])
async def list_files(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    stmt = select(FileModel).where(FileModel.transaction_id == transaction_id)
    result = await db.execute(stmt)
    files = result.scalars().all()
    return [FileResponse.model_validate(f) for f in files]


@router.post("/transactions/{transaction_id}/files", response_model=FileResponse)
async def upload_transaction_file(
    transaction_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
):
    file_id = await upload_file(file, db)
    # Link file to transaction
    file_record = await db.get(FileModel, file_id)
    if file_record:
        file_record.transaction_id = transaction_id
        await db.commit()
        await db.refresh(file_record)
    return FileResponse.model_validate(file_record)
