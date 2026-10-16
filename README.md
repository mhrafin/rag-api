# RAG API for Research

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688.svg)](https://fastapi.tiangolo.com/)
[![Postgres + pgvector](https://img.shields.io/badge/postgres-pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Docker Compose](https://img.shields.io/badge/docker-compose-ready-2496ED.svg)](docker-compose.yml)

A vanilla Retrieval-Augmented Generation (RAG) API: upload research documents, have them chunked and embedded in the background, then ask questions over the whole knowledge base with inline citations.

> Upload once → poll document status → `POST /query` for an evidence-based LLM answer with `[Ref N]` citations and traceable excerpts.

## Why use this

- **File-in, answers-out:** upload PDFs, text, markdown, and any other format supported by [Kreuzberg](https://github.com/kreuzberg-dev/kreuzberg); text is extracted automatically.
- **Crash-safe ingestion:** uploads commit a `document.created` event via the transactional outbox pattern. An independent worker polls `outbox_event` and runs chunking → embedding, so API restarts or embedding outages don't lose work.
- **Evidence-based answers:** retrieval uses `pgvector` cosine similarity (HNSW) + token-budgeted context, then `gpt-5-nano` answers with inline `[Ref N]` citations. Only cited refs are returned with `document_id`, `chunk_index`, and excerpts.
- **Cost visibility:** per-document `total_token` and `estimated_cost` tracking via `tiktoken` (`cl100k_base`).
- **Production basics built in:** shared-secret auth (`X-Auth-Token`), per-IP token-bucket rate limiting (10 burst, 2/sec), Alembic migrations, Docker Compose with `app` / `worker` / `migrate` / `db` / `adminer`.

## Architecture

```text
Client → FastAPI (src/main.py) → Postgres + pgvector
              │ writes document + outbox_event
              └── Worker (src/worker_main.py) polls outbox_event
                    ├── chunking_handler (RecursiveCharacterTextSplitter, 500/50)
                    └── embedding_handler (text-embedding-3-small)
                        → POST /query: vector search → gpt-5-nano → citations
```

- API entrypoint: `src/main.py:app`
- Worker entrypoint: `src.worker_main:main`
- See [docs/deployment.md](docs/deployment.md) and [docs/01-diagrams/worker_flow.md](docs/01-diagrams/worker_flow.md).

## Tech stack

| Layer | Choice |
| --- | --- |
| API | FastAPI 0.139, `asyncio` SQLAlchemy 2.0 |
| DB / vectors | PostgreSQL 18 + `pgvector`, HNSW `vector_cosine_ops` |
| Migrations | Alembic (`migrations/`) |
| Extraction | Kreuzberg (`extract_file`, MIME validation) |
| Chunking / tokens | LangChain text splitters, `tiktoken` |
| Embeddings / chat | LangChain OpenAI: `text-embedding-3-small`, `gpt-5-nano` |
| Packaging | `uv`, Docker, Docker Compose |

## Getting started

### Prerequisites

- Docker + Docker Compose (recommended), **or** Python 3.12+ with [`uv`](https://docs.astral.sh/uv/) + a reachable Postgres with `pgvector`
- An OpenAI API key

### 1. Configure

```bash
cp .env.example .env
# then edit .env
```

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `AUTH_SECRET` | yes | — | Value clients must send as `X-Auth-Token` |
| `DATABASE_URL` | yes | — | SQLAlchemy async URL, e.g. `postgresql+asyncpg://postgres:PASSWORD@127.0.0.1:5432/postgres_db` |
| `OPENAI_API_KEY` | yes | — | Used for embeddings and chat |
| `POSTGRES_PASSWORD` | yes (compose) | — | Compose `db` password |
| `POSTGRES_DB` | no | `postgres_db` | Compose `db` name |
| `EMBEDDING_DIM` | yes | `1536` | Must match `text-embedding-3-small` output |
| `TEMP_DIR` | no | `temp/` | Temp upload location |
| `COST_PER_MILLION` | no | `0.02` | Cost estimate per 1M tokens |
| `MAX_CONTEXT_STRING_TOKEN` | no | `10000` | Max retrieved context tokens per query |
| `WORKER_POLL_INTERVAL` | no | `5.0` | Worker outbox poll seconds |

See [.env.example](.env.example) and [docker-compose.yml](docker-compose.yml).

### 2. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

This starts:

- `app` → `http://localhost:8000` (`fastapi run src/main.py`)
- `worker` → `python -m src.worker_main` (scalable: `docker compose up --scale worker=2`)
- `migrate` → `alembic upgrade head` (one-shot, runs before `app`/`worker`)
- `db` → `pgvector/pgvector:pg18-trixie` on `:5432`
- `adminer` → `http://localhost:8080` (dev DB browser)

Interactive API docs: `http://localhost:8000/docs`

### 3. Run locally (without Docker)

```bash
uv sync
cp .env.example .env  # point DATABASE_URL at your pgvector DB

uv run alembic upgrade head
uv run fastapi run src/main.py --port 8000 --host 0.0.0.0
# in a second terminal:
uv run python -m src.worker_main
```

Health check:

```bash
curl -H "X-Auth-Token: $AUTH_SECRET" http://localhost:8000/health
# {"status":"healthy","database":"ok","query_result":1}
```

## Usage

All endpoints require `X-Auth-Token: <AUTH_SECRET>` except the auto-generated OpenAPI docs. Rate limit is 10 burst + 2/sec per IP (see `X-RateLimit-*` headers).

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | DB liveness check |
| `GET` | `/documents?limit=20&offset=0` | List documents |
| `POST` | `/documents` | Upload file (`multipart/form-data`, ≤50 MB) |
| `GET` | `/documents/{id}` | Get status, `total_token`, `estimated_cost` |
| `DELETE` | `/documents/{id}` | Delete document + chunks (cascade) |
| `POST` | `/query` | Ask the knowledge base |

### Upload a document

```bash
curl -X POST http://localhost:8000/documents \
  -H "X-Auth-Token: $AUTH_SECRET" \
  -F "file=@paper.pdf"
# {"id":1,"source_type":"file","source_reference":"paper.pdf","status":"queued"}
```

Document `status` flow: `queued` → `chunked` → `processed` (`failed` on error). Only `processed` chunks are queryable.

### Check processing status

```bash
curl -H "X-Auth-Token: $AUTH_SECRET" http://localhost:8000/documents/1
# {"id":1,"source_type":"file","source_reference":"paper.pdf",
#  "status":"processed","total_token":12345,"estimated_cost":0.00024}
```

### Query the knowledge base

```bash
curl -X POST http://localhost:8000/query \
  -H "X-Auth-Token: $AUTH_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does RAG combine retrieval and generation?", "top_k": 10}'
```

```json
{
  "response": "RAG combines a retriever [Ref 1] and a generator [Ref 2] ...",
  "references": [
    {"reference": "[Ref 1]", "document_id": 1, "chunk_index": 3, "excerpt": "..."}
  ]
}
```

Python example:

```python
import requests

BASE = "http://localhost:8000"
H = {"X-Auth-Token": "your-shared-secret"}

doc_id = requests.post(f"{BASE}/documents", headers=H,
    files={"file": open("paper.pdf", "rb")}).json()["id"]

answer = requests.post(f"{BASE}/query", headers=H,
    json={"query": "What datasets were used?", "top_k": 10}).json()
print(answer["response"])
print(answer["references"])
```

### List and delete

```bash
curl -H "X-Auth-Token: $AUTH_SECRET" "http://localhost:8000/documents?limit=20&offset=0"
curl -X DELETE -H "X-Auth-Token: $AUTH_SECRET" http://localhost:8000/documents/1
# 204 No Content
```

For full request/response schemas, use `/docs` (Swagger UI) when the app is running. Endpoint implementations live in [src/routers/](src/routers/).

## Project structure

```text
src/
  main.py              # FastAPI app, lifespan, routers, rate-limit middleware
  config.py            # pydantic-settings (.env)
  auth.py              # X-Auth-Token verification
  database.py          # async engine, session, pgvector init
  models.py            # Document, Chunk, OutboxEvent
  routers/             # documents.py, queries.py, health.py
  workers/             # worker.py + handlers/chunking_handler.py, embedding_handler.py
  worker_main.py       # worker entrypoint
  utils/               # embeddings.py, tokens.py
  middlewares.py / ratelimiter.py
migrations/            # Alembic versions
docs/
  deployment.md        # services, env, endpoints
  01-diagrams/worker_flow.md
  02-iterations/01-mvp-api.md  # requirements / scope
  03-adr/              # framework, datastore, ORM, extractor, retriever decisions
docker-compose.yml
Dockerfile
pyproject.toml
alembic.ini
```

## Documentation

- [docs/deployment.md](docs/deployment.md) — services, env vars, auth
- [docs/01-diagrams/worker_flow.md](docs/01-diagrams/worker_flow.md) — worker polling flow
- [docs/02-iterations/01-mvp-api.md](docs/02-iterations/01-mvp-api.md) — MVP requirements and scope
- [docs/03-adr/](docs/03-adr/) — architecture decision records
- [docs/local.md](docs/local.md) — local notes
- Live OpenAPI docs: `http://localhost:8000/docs` (when running)

## Getting help

- Start with the docs above and the inline `/docs` schema descriptions.
- For bugs or feature requests, please [open a GitHub issue](https://github.com/mhrafin/rag-api-for-research/issues) with steps to reproduce, expected vs. actual behavior, and relevant logs (`docker compose logs app worker db`).
- For local DB inspection, use Adminer at `http://localhost:8080` or connect directly to Postgres on `:5432`.

## Maintainers and contributing

Maintained by [@mhrafin](https://github.com/mhrafin) ([rag-api-for-research](https://github.com/mhrafin/rag-api-for-research)).

Contributions are welcome:

1. Fork and create a feature branch.
2. Use `uv sync` and match the existing style (Python 3.12, `ruff` — see `pyproject.toml`).
3. Run migrations (`uv run alembic upgrade head`) and test against a local `pgvector` DB.
4. Open a pull request describing the change and how you tested it.

No formal `CONTRIBUTING.md` or `LICENSE` file is committed yet — please check with the maintainer before redistributing or adding a license.
