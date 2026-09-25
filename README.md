# rag-api-for-research

A RAG API that turns your research paper collection into a citation-backed knowledge base. Upload PDFs, Markdown, or plain text. Get answers with inline sources.

<!-- > _Watch a demo_ (screenshot or GIF placeholder) -->

## Why

Traditional search gives you a pile of documents to read. rag-api-for-research gives you answers. Pulled from the right passages, cited to the right papers, delivered in a single response. Built because flipping between twenty PDF tabs to find one finding is a waste of good thinking.

## Quick Start

```bash
cp .env.example .env   # fill in your API keys
docker compose up       # app + pgvector + adminer
```

That's it. The app starts at `http://localhost:8000`.

To run without Docker:

```bash
uv sync --locked
uv run alembic upgrade head
uv run fastapi dev
```

## Usage

All endpoints require an `X-Auth-Token` header matching the `AUTH_SECRET` in your `.env`.

### Upload a document

```bash
curl -X POST http://localhost:8000/documents \
  -H "X-Auth-Token: your-secret" \
  -F "file=@paper.pdf"
```

Supported formats: `application/pdf`, `text/plain`, `text/markdown`. Max file size: 50 MB.

The server extracts text, splits it into chunks (500 tokens, 50-token overlap), embeds them with OpenAI `text-embedding-3-small`, and stores everything in pgvector with an HNSW index for fast similarity search.

### Ask a question

```bash
curl -X POST http://localhost:8000/query \
  -H "X-Auth-Token: your-secret" \
  -H "Content-Type: application/json" \
  -d '{"query": "What transformer architecture does this paper propose?", "top_k": 10}'
```

Returns a response with inline citations (`[Ref 1]`, `[Ref 2]`) mapped to source documents.

### Health check

```bash
curl -X GET http://localhost:8000/health \
  -H "X-Auth-Token: your-secret"
```

## Architecture

```
┌────────────┐   ┌───────────┐   ┌────────────┐   ┌───────────┐   ┌──────────┐
│  Upload    │ → │ Kreuzberg │ → │ Chunk (500 │ → │ Embed     │ → │ pgvector  │
│  PDF/txt/md│   │ extract   │   │ tok, 50 ov)│   │ text-emb-3 │   │ HNSW idx │
└────────────┘   └───────────┘   └────────────┘   └───────────┘   └──────────┘
                                                                       ↓
┌────────────┐   ┌───────────┐   ┌────────────────────┐   ┌──────────────────┐
│  Ask       │ → │ Embed     │ → │ pgvector cosine    │ → │ gpt-5-nano       │
│  question  │   │ query     │   │ distance search    │   │ + inline cites   │
└────────────┘   └───────────┘   └────────────────────┘   └──────────────────┘
```

- **FastAPI** with async asyncpg + SQLAlchemy
- **pgvector** with HNSW index (`m=16`, `ef_construction=64`, `vector_l2_ops`)
- **LLM**: `gpt-5-nano` via langchain `ChatOpenAI` (`temperature=0.5`, `reasoning_effort=minimal`)
- **Chunking**: `RecursiveCharacterTextSplitter`, `cl100k_base` encoding

## Contributing

```bash
git clone https://github.com/mhrafin/rag-api-for-research
cd rag-api-for-research
uv sync --locked
uv run alembic upgrade head
uv run fastapi dev
```

Open a PR against `main`. All contributions welcome.
