# NoiseMap

An API that places every post on a map of meaning. You see what is being said, who is saying it, and whether the crowd saying it is real or fake. An entry to the Hostinger challenge "Decode the Noise" at [Junction 2026](https://2026.hackjunction.com/) (Espoo, 13 to 15 November 2026).

**Live:** <https://noisemap.srv2160938.hstgr.cloud> (Hostinger VPS).

**Status:** a workspace maps your own posts through the API (`POST /api/v1/items`) as they arrive. The demo map shows 100,000 posts from X, a sample of the public dataset [`SinclairSchneider/tweets_sample_2026`](https://huggingface.co/datasets/SinclairSchneider/tweets_sample_2026) (nearly all dated January to July 2026): every post of 38,088 actors the probes never trained on, a seeded draw except 26 accounts kept on purpose for the demonstration. The posts are embedded with EmbeddingGemma on a Verda GPU and the 48 zones are named by Gemini through the Hostinger AI Router. A pasted text or link is placed on the map live. A layer appears in the product only once its evaluation report exists: the method page of the site lists what is measured. How each partner technology is used: [`docs/tech-challenge-status.md`](docs/tech-challenge-status.md).

## What is here

| Path | Content |
| --- | --- |
| [`frontend/`](frontend/) | The web app: React, TypeScript, Vite, deck.gl. The point cloud in 2D and 3D, colour by attribute, legend, filters, search, time window, lasso, neighbours by meaning |
| [`backend/`](backend/) | The API: FastAPI. Loads one map build at start-up; serves typed arrays, item content, search by words and similarity by meaning |
| [`pipelines/`](pipelines/) | Offline steps that make a map build: ingest, embed, layout, neighbours, zones, pack |
| [`deploy/`](deploy/) | Images and the Compose stack of the server |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Checks, image build and deploy, on CRACI runners |
| [`reports/`](reports/) | Run log of the pipeline, the account of the Verda run; evaluation reports to come |
| [`docs/`](docs/) | The brief, the specification ([`docs/spec.md`](docs/spec.md)), research, Hostinger notes, tech challenges |

## Run it locally

Needs [uv](https://docs.astral.sh/uv/), Node.js 22 and [Ollama](https://ollama.com/) with `ollama pull embeddinggemma:300m-qat-q8_0`.

```
cp .env.example .env

# 1. Make a small map build under data/build/ (downloads the dataset on first run)
uv run --group pipelines python -m pipelines.ingest --help

# 2. API on :8000, serving data/build/current
uv run uvicorn backend.main:app --port 8000

# 3. Web app on :5173, proxying /api to the API
cd frontend && npm install && npm run dev
```

Checks:

```
uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npx tsc -b && npm run build
```

## How it is deployed

A push to `main` runs the checks on CRACI runners, builds the two images there, copies them to the Hostinger VPS over SSH and starts the stack ([`deploy/docker-compose.yml`](deploy/docker-compose.yml)): the API, the static web app and an Ollama container with EmbeddingGemma, published by the Traefik proxy that the server already runs. Map builds are made offline and copied to the server; they never go through git.

## Licence

[MIT](LICENSE). All code in this repository was written during the event.
