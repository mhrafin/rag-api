import logging
import os
import uuid

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
)
from fastapi.responses import Response

logger = logging.getLogger(__name__)
from kreuzberg import ExtractionConfig, extract_file, validate_mime_type
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import verify_auth_secret
from src.config import get_settings
from src.database import get_session
from src.models import Document, OutboxEvent

settings = get_settings()

router = APIRouter(dependencies=[Depends(verify_auth_secret)])


class DocumentResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    id: int
    source_type: str
    source_reference: str
    status: str


@router.post("/documents", response_model=DocumentResponse)
async def documents(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
):

    MAX_FILE_SIZE = 50 * 1024 * 1024

    if file.size and file.size > MAX_FILE_SIZE:
        return Response(status_code=413, content="File too large")

    normalized_mime = resolve_mime_type(file.content_type)
    if normalized_mime is None:
        return Response(
            status_code=415,
            content=f"Unsupported file format: {file.content_type}",
        )

    os.makedirs(settings.temp_dir, exist_ok=True)

    # To stop traversal attacks
    file_path = (
        settings.temp_dir + str(uuid.uuid4()) + "." + normalized_mime.split("/")[-1]
    )

    # We need to save the file. Background tasks can't continue with the file from UploadFile when the request life-cycle ends, because UploadFile is temporary.
    async with aiofiles.open(f"{file_path}", "wb") as buffer:
        await file.seek(0)
        while chunk := await file.read(1024 * 1024):
            await buffer.write(chunk)

    content = await extract_content(file_path=file_path, mime_type=normalized_mime)
    # print(content)

    new_doc = Document(
        source_type="FILE",
        source_reference=file.filename,
        content=content,
        status="QUEUED",
    )

    session.add(new_doc)

    # Need to flush to get the new doc id without writing to the db
    await session.flush()

    event = OutboxEvent(aggregate_id=new_doc.id, type="document.created")
    session.add(event)

    await session.commit()

    await session.refresh(new_doc)

    os.remove(file_path)

    return new_doc


def resolve_mime_type(raw_mime_type: str | None) -> str | None:
    if not isinstance(raw_mime_type, str):
        return None

    cleaned = raw_mime_type.strip().split(";")[0].strip().lower()
    if not cleaned:
        return None

    try:
        return validate_mime_type(cleaned)
    except (RuntimeError, ValueError, TypeError):
        logger.info("Unsupported file format: %r", raw_mime_type)
        return None


async def extract_content(file_path: str, mime_type: str | None = None):
    try:
        config = ExtractionConfig()
        result = await extract_file(file_path, mime_type=mime_type, config=config)
        return result.content
    except Exception as e:
        logger.error("extract_content failed for %s: %s", file_path, e)
        raise


class DocumentIDResponse(BaseModel):
    id: int
    source_type: str
    source_reference: str
    status: str
    total_token: int | None
    estimated_cost: float | None


@router.get("/documents/{id}", response_model=DocumentIDResponse)
async def documents_get(id: int, db: AsyncSession = Depends(get_session)):
    stmt = select(Document).where(Document.id == id)

    result = await db.execute(stmt)

    doc = result.scalar()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc
