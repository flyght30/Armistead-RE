import logging
import uuid
from uuid import UUID
from fastapi import HTTPException, UploadFile
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import Settings
from app.models.file import File

logger = logging.getLogger(__name__)
settings = Settings()

# Initialize MinIO client
minio_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False,
)

BUCKET_NAME = "armistead-documents"


async def upload_file(file: UploadFile, db: AsyncSession) -> UUID:
    """Upload a file to MinIO/S3 and record it in the database."""
    allowed_types = ["application/pdf", "image/jpeg", "image/png"]
    if file.content_type not in allowed_types:
        raise ValueError(f"Unsupported file type: {file.content_type}")

    contents = await file.read()
    if len(contents) > 25 * 1024 * 1024:
        raise ValueError("File size exceeds 25MB limit")

    await file.seek(0)
    file_ext = file.filename.split(".")[-1] if file.filename else "bin"
    object_name = f"{uuid.uuid4()}.{file_ext}"

    # Ensure bucket exists
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)

    # Upload to MinIO
    minio_client.put_object(
        BUCKET_NAME,
        object_name,
        file.file,
        length=len(contents),
        content_type=file.content_type,
    )

    presigned_url = minio_client.presigned_get_object(BUCKET_NAME, object_name)

    new_file = File(
        name=object_name,
        content_type=file.content_type,
        url=presigned_url,
        transaction_id=None,
    )
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)

    return new_file.id


async def get_file_url(file_id: UUID, db: AsyncSession) -> str:
    """Get a presigned URL for a stored file."""
    file_record = await db.get(File, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    return file_record.url
