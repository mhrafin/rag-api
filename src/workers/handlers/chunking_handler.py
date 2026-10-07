import asyncio
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import get_settings
from src.models import Chunk, Document, OutboxEvent
from src.utils.tokens import get_token_count


async def chunk_document(document: Document, session):
    # await asyncio.sleep(10.0)

    try:
        settings = get_settings()
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base", chunk_size=500, chunk_overlap=50
        )

        splitted_chunks = await asyncio.to_thread(
            text_splitter.split_text, document.content
        )

        doc_total_token = 0
        for index, chunk in enumerate(splitted_chunks):
            token_count = get_token_count(chunk)
            doc_total_token += token_count
            new_chunk = Chunk(
                document_id=document.id,
                chunk_uuid=uuid.uuid4(),
                chunk_index=index + 1,
                content=chunk,
                token_count=token_count,
            )
            # await asyncio.sleep(10.0)

            session.add(new_chunk)

            await session.flush()

        document.total_token = doc_total_token

        # Add estimated cost of the total operation
        current_est_cost_doc = (
            0.0 if document.estimated_cost is None else document.estimated_cost
        )
        new_est_cost_doc = (
            (settings.cost_per_million / 1000000) * doc_total_token
        ) + current_est_cost_doc
        document.estimated_cost = new_est_cost_doc

        document.status = "CHUNKED"

        new_event = OutboxEvent(aggregate_id=document.id, type="document.chunked")

        session.add(new_event)

        await session.flush()
        return True
    except Exception:
        document.status = "FAILED"
        await session.flush()
        return False
