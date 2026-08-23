import enum
import uuid
from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    TIMESTAMP,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import get_settings

settings = get_settings()

# https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#using-python-enum-or-pep-586-literal-types-in-the-type-map


class DocSourceTypeEnum(enum.Enum):
    FILE = "file"
    URL = "url"


class DocStatusEnum(enum.Enum):
    QUEUED = "queued"
    CHUNKED = "chunked"
    PROCESSED = "processed"
    FAILED = "failed"


# This is how its done, https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html
class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "document_table"

    # Types: https://docs.sqlalchemy.org/en/20/core/types.html
    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[DocSourceTypeEnum]
    source_reference: Mapped[str]
    content: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[DocStatusEnum]
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    # https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html#one-to-many
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")
    total_token: Mapped[int] = mapped_column(nullable=True)
    estimated_cost: Mapped[float] = mapped_column(nullable=True)


class Chunk(Base):
    __tablename__ = "chunk_table"

    # no two rows in the chunks table can share the same (document_id, chunk_index) pair.
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("document_table.id", ondelete="CASCADE")
    )
    document: Mapped["Document"] = relationship(back_populates="chunks")
    # Need a chunk_uuid to trace back to the chunk
    chunk_uuid: Mapped[UUID] = mapped_column(
        Uuid, unique=True, nullable=False, default=uuid4
    )
    chunk_index: Mapped[int]
    content: Mapped[str]
    token_count: Mapped[int] = mapped_column(nullable=True)
    # https://github.com/pgvector/pgvector-python#sqlalchemy
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_event"

    # https://yasir323.hashnode.dev/transactional-outbox-pattern-python#the-write-side-in-code
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    aggregate_id: Mapped[str] = mapped_column(String)
    type: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


Index("idx_id", OutboxEvent.id, postgresql_where=(OutboxEvent.status == "pending"))
Index("idx_aggregate_id_type", OutboxEvent.aggregate_id, OutboxEvent.type)

# https://github.com/pgvector/pgvector-python#sqlalchemy
Index(
    "chunk_embedding_hnsw_index",
    Chunk.embedding,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
