from typing import Optional
import uuid
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_async_session
from app.models.file import File

async def upload_file(file: UploadFile, db: AsyncSession = Depends(get_async_session)) -> str:
    if file.content_type not in ["application/pdf", "image/jpeg", "image/png"]:
        raise ValueError("Unsupported file type")
    
    if len(await file.read()) > 25 * 1024 * 1024:
        raise ValueError("File size exceeds limit")

    file.filename = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    await file.seek(0)

    # Save file to S3/MinIO
    s3_client = settings.s3_client
    response = s3_client.upload_fileobj(file.file, settings.bucket_name, file.filename)
    
    new_file = File(
        id=uuid.uuid4(),
        name=file.filename,
        content_type=file.content_type,
        url=s3_client.generate_presigned_url('get_object', Params={'Bucket': settings.bucket_name, 'Key': file.filename}, ExpiresIn=900),
        transaction_id=None
    )
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)

    return new_file.id

async def get_file_url(file_id: UUID, db: AsyncSession = Depends(get_async_session)) -> str:
    file = await db.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return file.url
