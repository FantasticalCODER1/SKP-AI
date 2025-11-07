# Session Knowledge Profile AI (SKP-AI)

Session Knowledge Profile AI (SKP-AI) assembles a focused knowledge base for every chat session. When a user starts a session with a topic, SKP-AI launches a research pipeline that discovers, cleans, ranks, embeds, and synthesizes information. Once the build is complete, the chat endpoint serves retrieval-augmented answers grounded in the generated session knowledge profile.

## Architecture Overview

```
start_session → queued → discover → clean → rank → embed → synthesize → ready
                                            │
                                            └──► ChromaDB vector store per session
```

* **FastAPI** application with modular routers for health, build, and chat endpoints.
* **ThreadPoolExecutor** drives asynchronous build jobs while persisting progress to the filesystem.
* **Pipelines** implement scraping, cleaning, ranking, embedding, synthesizing, and answering.
* **ChromaDB** stores per-session embeddings for retrieval.
* **OpenAI models** provide embeddings (`text-embedding-3-large`), summarization (`gpt-4o-mini`), and chat answers (`gpt-5`). Model names are configurable via environment variables.
* **Prometheus metrics** exposed at `/metrics`.

### Data Layout

Each session writes artifacts to `data/skp_cache/skp_<session_id>/`:

* `skp.json` – synthesized summary with evidence ledger and document manifest.
* `state.json` – serialized `SessionState` used to resume progress.
* `manifest.json` – chunk metadata stored alongside embeddings.
* `chroma/` – persistent ChromaDB collection for retrieval.

## API Endpoints

### `POST /start_session`
Creates a new session and begins the build pipeline asynchronously.

Request body:
```json
{"topic": "electric cars vs hybrids", "user_context": {"region": "US"}}
```

Response (202 Accepted):
```json
{"session_id": "<uuid>", "status": "queued"}
```

### `GET /session_status/{session_id}`
Returns the current stage, elapsed time, and ETA.

Example response:
```json
{
  "session_id": "<uuid>",
  "topic": "electric cars vs hybrids",
  "stage": "embed",
  "elapsed_seconds": 42.3,
  "eta_seconds": 58.0,
  "detail": "Embedding knowledge base"
}
```

### `POST /ask/{session_id}`
Answers questions using the built knowledge base. Until the pipeline reaches the `ready` stage, the endpoint responds with HTTP 409.

Example 409 response:
```json
{
  "detail": {
    "status": "building",
    "stage": "embed",
    "eta_seconds": 42.5
  }
}
```

When ready, the endpoint returns an `AnswerContract`:
```json
{
  "answer": {
    "summary": "...\n\nThis information is for general educational purposes only.",
    "reasoning_points": ["..."],
    "next_steps": ["..."],
    "risks": ["..."],
    "citations": [{"id": "S01", "title": "...", "url": "...", "source": "..."}],
    "assumptions": ["..."],
    "confidence": 0.72
  }
}
```

## Environment Variables

Copy `.env.example` to `.env` and update the values:

| Variable | Description |
| --- | --- |
| `OPENAI_API_KEY` | Required for OpenAI API calls. |
| `PORT` | Uvicorn server port (default `8000`). |
| `SAFE_SCRAPE` | When `true`, scrape live allowlisted pages. When `false`, read from cached samples. |
| `RATE_LIMIT_RPS` | Per-IP requests per second. |
| `MAX_SCRAPE_DOCS` | Maximum documents to fetch during discovery. |
| `TOP_K_RETRIEVAL` | Retrieval depth for answering questions. |
| `MODEL_EMBED`, `MODEL_SUMMARY`, `MODEL_CHAT` | Model identifiers for embeddings, synthesis, and chat. |
| `ALLOWLIST_PATH` | Path to the scrape domain allowlist. |
| `SKP_CACHE_PATH` | Directory for session artifacts. |
| `ROBOTS_CACHE_PATH` | Directory for cached `robots.txt` files. |

## Local Development

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add OPENAI_API_KEY
make run
```

The default run command serves the API at `http://127.0.0.1:8000`.

## Docker

```bash
docker-compose up --build
```

The API becomes available at `http://localhost:8000` with session cache persisted to the host `data/` directory.

## Example Usage

```bash
curl -X POST http://localhost:8000/start_session \
     -H "Content-Type: application/json" \
     -d '{"topic":"electric cars vs hybrids"}'

curl http://localhost:8000/session_status/<id>

curl -X POST http://localhost:8000/ask/<id> \
     -H "Content-Type: application/json" \
     -d '{"question":"Compare efficiency factors"}'
```

## Notes

* Live scraping obeys `robots.txt` and the configured allowlist.
* The chat endpoint is informational only and appends the disclaimer “This information is for general educational purposes only.” to every summary.
* Prometheus metrics are available at `/metrics` for integration with observability stacks.
