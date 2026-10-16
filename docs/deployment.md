# Deployment

Vanilla RAG API (`src/main.py:app`).

## Services (`docker-compose.yml`)


| Service   | Image / Command                      | Notes                                                                               |
| --------- | ------------------------------------ | ----------------------------------------------------------------------------------- |
| `app`     | `fastapi run src/main.py` on `:8000` | Requires`DATABASE_URL`, `AUTH_SECRET`, `EMBEDDING_DIM`, `OPENAI_API_KEY`            |
| `worker`  | `python -m src.worker_main`          | Polls `outbox_event` every `WORKER_POLL_INTERVAL` (default `5.0s`); independent of `app`, safe to `--scale worker=N` via `skip_locked`; needs same DB/OpenAI env as `app` |
| `migrate` | `alembic upgrade head` (one-shot)    | Runs after `db` healthy, before `app`/`worker` (`service_completed_successfully`)   |
| `db`      | `pgvector/pgvector:pg18-trixie`      | Persists`document_table`, `chunk_table`, `outbox_event`; needs `pgvector` extension |
| `adminer` | `:8080`                              | Dev-only DB browser                                                                 |

## Env

See `.env.example`: `AUTH_SECRET`, `DATABASE_URL`, `OPENAI_API_KEY`, `EMBEDDING_DIM=1536`, `TEMP_DIR`, `COST_PER_MILLION`, `MAX_CONTEXT_STRING_TOKEN`, `WORKER_POLL_INTERVAL=5.0`.

## Endpoints

All gated by `X-Auth-Token: <AUTH_SECRET>`.
