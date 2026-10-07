from src.config import get_settings
from src.models import Document
from src.utils.embeddings import embed_text


async def embed_chunks(document: Document, session):
    try:
        settings = get_settings()
        chunks = [c for c in document.chunks if c.embedding is None]
        chunk_contents = [c.content for c in chunks]
        vectors = await embed_text(chunk_contents, settings)
        for vector, chunk in zip(vectors, chunks):
            chunk.embedding = vector

        document.status = "PROCESSED"
        await session.flush()
        return True
    except Exception:
        document.status = "FAILED"
        await session.flush()
        return False
