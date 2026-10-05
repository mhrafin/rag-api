# RAG API

\*\*Upload Documents. Ask questions. Get thorough answers with inline `[Ref N]` citations you can actually trace

## Quick Start

The fastest way — Docker Compose (API + Postgres/pgvector + migrator + Adminer):

### 1. Configure

```bash
cp .env.example .env
# Edit .env — at minimum set:
# AUTH_SECRET=your-shared-secret
# OPENAI_API_KEY=sk-...
# POSTGRES_PASSWORD=...
# EMBEDDING_DIM=1536
```

### 2. Run

```bash
docker compose up --build
```

### 3. Try it

```bash
# Health check
curl -H "X-Auth-Token: your-shared-secret" http://localhost:8000/health

# Interactive docs
open http://localhost:8000/docs
```

That's it. Upload a document, wait for `PROCESSED`, and start querying.

---

## Usage

All endpoints are gated by `X-Auth-Token: <AUTH_SECRET>`.

| Method | Endpoint          | What it does                                        |
| ------ | ----------------- | --------------------------------------------------- |
| `GET`  | `/`               | Hello-world (auth check)                            |
| `GET`  | `/health`         | App + DB liveness (`SELECT 1`)                      |
| `POST` | `/documents`      | Upload a file (`multipart/form-data`, field `file`) |
| `GET`  | `/documents/{id}` | Check status, token count, estimated cost           |
| `POST` | `/query`          | Ask the corpus, get answer + references             |

### Upload a document

Max **50 MB**. Extraction via [Kreuzberg](https://github.com/kreuzberg-dev/kreuzberg).

```bash
curl -X POST http://localhost:8000/documents \
  -H "X-Auth-Token: your-shared-secret" \
  -F "file=@./paper.pdf;type=application/pdf"
# => {"id": 1, "source_type": "FILE", "source_reference": "paper.pdf", "status": "QUEUED"}
```

What happens next (background pipeline in `src/routers/documents.py`):

1. `QUEUED` → chunk with `RecursiveCharacterTextSplitter` (tiktoken `cl100k_base`, chunk size **500**, overlap **50**)
2. `CHUNKED` → embed with `text-embedding-3-small`, store in pgvector (`HNSW`, cosine ops)
3. `PROCESSED` → queryable. `FAILED` on error. Token count (`tiktoken`) and estimated cost tracked per document.

Poll status:

```bash
curl -H "X-Auth-Token: your-shared-secret" http://localhost:8000/documents/1
# => {"id":1,"source_type":"FILE","source_reference":"paper.pdf","status":"PROCESSED","total_token":12403,"estimated_cost":0.000248...}
```

### Ask a question

```bash
curl -X POST http://localhost:8000/query \
  -H "X-Auth-Token: your-shared-secret" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does RAG combine retrieval and generation?", "top_k": 10}'
```

```json
{
  "response": "RAG combines a retriever [Ref 1] and a generator [Ref 2] to answer questions...",
  "references": [
    {
      "reference": "[Ref 1]",
      "document_id": 1,
      "chunk_index": 3,
      "excerpt": "..."
    },
    {
      "reference": "[Ref 2]",
      "document_id": 2,
      "chunk_index": 7,
      "excerpt": "..."
    }
  ]
}
```

Request rules:

- `query`: 1–2000 chars, required
- `top_k`: 1–15, default `10`
- Context is token-budgeted (`MAX_CONTEXT_STRING_TOKEN`, default `10000`) — retrieval stops before overflow
- Only `PROCESSED` documents are searched
- LLM: `gpt-5-nano` with strict inline-citation prompt; only refs actually cited in the answer are returned (excerpt truncated to 500 chars)

### Configuration

See `.env.example`:

| Var                                 | Default | Purpose                                                                 |
| ----------------------------------- | ------- | ----------------------------------------------------------------------- |
| `AUTH_SECRET`                       | —       | Shared secret for`X-Auth-Token` header                                  |
| `DATABASE_URL`                      | —       | e.g.`postgresql+asyncpg://postgres:PASSWORD@127.0.0.1:5432/postgres_db` |
| `OPENAI_API_KEY`                    | —       | Embeddings + chat                                                       |
| `EMBEDDING_DIM`                     | `1536`  | Must match`text-embedding-3-small` / `Vector(N)` column                 |
| `TEMP_DIR`                          | `temp/` | Staging dir for uploads                                                 |
| `COST_PER_MILLION`                  | `0.02`  | Cost estimate math per doc                                              |
| `MAX_CONTEXT_STRING_TOKEN`          | `10000` | Cap on retrieved context per query                                      |
| `POSTGRES_PASSWORD` / `POSTGRES_DB` | —       | Compose DB bootstrap                                                    |

Other behavior worth knowing:

- **Rate limiting:** token-bucket middleware (`10` burst, `2`/sec refill) — see `src/ratelimiter.py`, `src/middlewares.py`.
- **Outbox pattern:** every document insert also writes `outbox_event(document.created)` — the intended hook for a durable relay worker that survives API restarts.
- **HNSW index:** `chunk_embedding_hnsw_index` (`m=16`, `ef_construction=64`, `vector_cosine_ops`) for fast similarity search.

---

## Contributing

### Clone the repo

```bash
git clone https://github.com/<you>/rag-api-for-research.git
cd rag-api-for-research
```

### Run the stack locally (recommended)

```bash
cp .env.example .env
docker compose up --build
# API:      http://localhost:8000/docs
# Adminer:  http://localhost:8080 (dev-only DB browser)
```

### Run without Docker (API only)

Requires Python `>=3.12`, [uv](https://docs.astral.sh/uv/), and a reachable Postgres with `pgvector`.

```bash
uv sync --locked
cp .env.example .env  # point DATABASE_URL at your DB
uv run alembic upgrade head
uv run fastapi run src/main.py --port 8000
```

Useful extras:

```bash
# DB migrations
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head

# C4 diagrams (docs/01-c4)
docker pull structurizr/structurizr
docker run -it --rm -p 8081:8080 --user "$(id -u):$(id -g)" \
  -v ./docs/01-c4:/usr/local/structurizr structurizr/structurizr local
# then visit http://localhost:8081 — see docs/local.md
```

### Submit a pull request

If you'd like to contribute, please fork the repository and open a pull request to the `main` branch. Good first targets live in `docs/kanban.md` — e.g. broader Kreuzberg format support, a durable outbox relay worker, and list/delete document endpoints. Design context: `docs/02-iterations/01-mvp-api.md`, `docs/deployment.md`, `docs/03-adr/`.
