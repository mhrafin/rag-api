# Deployment

Vanilla RAG API (`src/main.py:app`).

## Services (`docker-compose.yml`)


| Service   | Image / Command                      | Notes                                                                               |
| --------- | ------------------------------------ | ----------------------------------------------------------------------------------- |
| `app`     | `fastapi run src/main.py` on `:8000` | Requires`DATABASE_URL`, `AUTH_SECRET`, `EMBEDDING_DIM`, `OPENAI_API_KEY`            |
| `migrate` | `alembic upgrade head` (one-shot)    | Must complete before`app` serves traffic                                            |
| `db`      | `pgvector/pgvector:pg18-trixie`      | Persists`document_table`, `chunk_table`, `outbox_event`; needs `pgvector` extension |
| `adminer` | `:8080`                              | Dev-only DB browser                                                                 |

## Env

See `.env.example`: `AUTH_SECRET`, `DATABASE_URL`, `OPENAI_API_KEY`, `EMBEDDING_DIM=1536`, `TEMP_DIR`, `COST_PER_MILLION`, `MAX_CONTEXT_STRING_TOKEN`.

## Endpoints

All gated by `X-Auth-Token: <AUTH_SECRET>`.
