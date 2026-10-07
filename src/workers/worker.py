import asyncio

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.database import async_session_maker
from src.models import Document, OutboxEvent
from src.workers.handlers.chunking_handler import chunk_document
from src.workers.handlers.embedding_handler import embed_chunks


class Worker:
    def __init__(self, poll_interval: float = 1.0):

        self.poll_interval = poll_interval

    async def start(self):
        while True:
            async with async_session_maker() as session:
                # print("Hello I am worker")
                stmt = (
                    select(OutboxEvent)
                    .where(OutboxEvent.status == "pending")
                    .order_by(OutboxEvent.created_at, OutboxEvent.aggregate_id)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                event = await session.scalar(stmt)

                if event is not None:
                    try:
                        doc = await session.scalar(
                            select(Document)
                            .where(Document.id == event.aggregate_id)
                            .options(selectinload(Document.chunks))
                        )
                        if doc is None:
                            event.status = "missing"
                            event.processed_at = func.now()
                            await session.commit()
                            continue

                        # print(event.id)
                        if event.type == "document.created":
                            # Hand over to chunking handler
                            chunked = await chunk_document(
                                document=doc, session=session
                            )

                            if chunked:
                                event.status = "done"
                            else:
                                event.status = "failed"

                            event.processed_at = func.now()
                            await session.commit()
                            continue
                        if event.type == "document.chunked":
                            # Hand over to embedding handler
                            embedded = await embed_chunks(document=doc, session=session)

                            if embedded:
                                event.status = "done"
                            else:
                                event.status = "failed"

                            event.processed_at = func.now()
                            await session.commit()
                            continue

                    except Exception as e:
                        await session.rollback()
                        event.status = "failed"
                        event.processed_at = func.now()
                        await session.commit()

            await asyncio.sleep(self.poll_interval)
