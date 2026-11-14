# Tech challenges: what is in place

State on 14 Nov 2026, evening. Companion to [`tech-challenge-plan.md`](tech-challenge-plan.md): the plan says what we enter and why; this file says how each entry is done today, what was measured, and what is still to do. Every figure here was measured on our machines; where it is recorded is given beside it.

Live product: <https://noisemap.srv2160938.hstgr.cloud>, served from the Hostinger VPS.

## 1. Summary

| Challenge | In the product today | Still to do |
| --- | --- | --- |
| Gemma | Every point of the map is an EmbeddingGemma vector. The same weights answer live on the 2 vCPU server: search by meaning, reliefs, the paste box | Probes on those vectors (no detector yet). The comparison with other embedding models on a labelled sample. Gemma as a local LLM: not started |
| Verda | A GPU instance embedded 134,200 posts with the same weights, 131 per second against 14 to 21 on the laptop, and ran the layout, the neighbours and the zones. The 120,000-point build shipped to the VPS as files and is the one live | The summary link in Verda's Discord. The embedding model comparison as a second use |
| Gemini API | The 48 zones of the live map are named by `gemini-3.8-flash` through the Hostinger AI Router: one call per zone, typed output, cached | The main use, the technique pass on flagged items, needs the probes first |
| Context.dev | A pasted link is read through their scrape endpoint and placed on the map like a pasted text | Verdicts on the page once detectors exist. Reading the links a swarm shares most (stretch) |
| CRACI | The whole CI/CD runs on their runners: checks, image builds, deploy to the VPS | Using the build data itself (SBOM of the deployed commit shown in the product): not started, needs `CRACI_API_TOKEN` |

## 2. Which model runs where

This is the answer to "is it a hosted API or does it run locally?".

| Work | Model | Mode | Where it runs today |
| --- | --- | --- | --- |
| Embedding the corpus (offline) | EmbeddingGemma, tag `embeddinggemma:300m-qat-q8_0` | Local: open weights behind an Ollama endpoint we start | A Verda A100 instance for the live build (120,000 posts); the laptop for the two first builds (3,000 and 18,000 posts) |
| Embedding a query live (search by meaning, relief by concept, paste box) | The same weights, same tag | Local | An Ollama container beside the API on the Hostinger VPS, CPU only, not published |
| Naming the zones (offline) | `gemini-3.8-flash` | Hosted | The Hostinger AI Router (`https://router.hostinger.com/v1`) |
| Reading the page behind a pasted link (live) | none | Hosted service | Context.dev |

**No hosted embedding API is called.** The reasons:

- The AI Router lists two embedding models, both OpenAI's (`text-embedding-3-small`, `text-embedding-3-large`), and no Gemma one. Checked on the Router's model list with our key.
- A map build is tied to one embedding key. Another model means embedding the whole corpus again and refitting every probe.
- The Gemma entry rests on the open weights running on the small server.

**The switch between local and hosted exists, as configuration.** Every embedding call goes through one OpenAI-compatible client (`backend/model_client/embedding.py`), set by values in `.env`: `EMBEDDING_API_BASE`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`, plus `EMBEDDING_REVISION`, `EMBEDDING_PREFIX` and `EMBEDDING_DIMS`, which complete the key. Pointing them at the AI Router would work with no code change, at the price of a new build. It is not an option in the interface, on purpose: mixing vectors of two models gives wrong neighbours silently. The server enforces it: when its key differs from the key of the build it serves, the similarity and paste routes answer 503 instead of comparing.

The LLM role has the same three values (`LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL`) and one client (`backend/model_client/llm.py`).

The key of the deployed build: `embeddinggemma:300m-qat-q8_0@e84a7acc2394|prefix='task: classification | query: '|dims=256`. That is: the 8-bit quantisation-aware weights, the digest Ollama reports, one prompt prefix for every text offline and live, and the first 256 of 768 dimensions, renormalised.

What was measured:

| Question | Result | Recorded in |
| --- | --- | --- |
| Throughput on the laptop CPU (Snapdragon X), 8-bit tag | 20.9 posts per second on 3,000 posts, 14.0 on 18,000 | `reports/pipeline-runs.jsonl` |
| Throughput of the default 16-bit tag on the same laptop | 2.4 posts per second: the reason for the 8-bit tag | Pipeline run of 14 Nov, not in the run log |
| Are the two tags interchangeable? | No: cosine 0.981 on average between them on 120 texts, 10-nearest overlap 0.86. A build and its live queries use one tag | Same |
| Same weights, another machine: same vectors? | Against the laptop's cached vectors, on 100 texts: Verda A100, cosine 0.99985 on average (minimum 0.99972); the VPS, 0.99985 (minimum 0.99941) | `reports/pipeline-runs.jsonl`, step `embed-check` |
| Live latency on the VPS, measured from outside over HTTPS | Similarity to a text: 1.8 s for the first call (model load), then 0.36 to 0.55 s. Paste box: 1.2 s for a text, 2.7 s for a link | Not recorded: one manual run on 14 Nov |
| Memory on the VPS | Ollama container 717 MiB, API 56 to 63 MiB with 18,000 points | Same |

## 3. The entries

### 3.1 Gemma

**How it is done.** `pipelines/embed` sends each post, with the prefix, to an Ollama endpoint and stores unit vectors with their key. `pipelines/layout`, `neighbours` and `zones` read those vectors only. On the server, `deploy/docker-compose.yml` runs `ollama/ollama` with the same tag; the API embeds a query with it and does one matrix product against the vectors in memory (`backend/search/meaning.py`, `backend/analyze/`). No GPU and no paid call at query time.

**What the user sees of it.** Neighbours by meaning of any point, "raise what resembles these words" (a relief by concept), "what resembles this selection", and the paste box.

**Not done yet.** The probes, which are the point of the angle ("every probe is a linear read-out of the vector"). The comparison of EmbeddingGemma with Qwen3-Embedding on a labelled sample (plan §3). Gemma as the local LLM for the technique pass.

### 3.2 Verda

**How it is done.** The pipeline is the same code on any machine: clone the repository on a GPU instance, run Ollama there with the same tag, check the digest, run `ingest`, `embed`, `layout`, `neighbours`, `zones`, `pack`, bring the build folder back and copy it to the VPS. Instances are created and deleted through Verda's API with the team's credentials. One line per step goes to `reports/pipeline-runs.jsonl` with the machine named.

**What ran.** One instance of type `1A100.22V` (one A100, 80 GB) in Finland, up 50 minutes, 1.83 EUR of credits, deleted afterwards. Full account: [`reports/verda.md`](../reports/verda.md).

| Step, on the Verda instance | Measured |
| --- | --- |
| Embed | 134,200 texts in 1,023 s: 131 per second. The laptop does 14 to 21 per second, so 14,300 to 21,400 texts in the same time |
| Layout (UMAP in 3D and in 2D), 120,000 points | 209 s |
| Neighbours, exact, 10 per point | 75 s |
| Zones | 5 s |

A second layout of the same vectors, on their three axes of largest variance (PCA), was made on the laptop in 5 s and is the one served since 14 Nov evening, as a test: those three axes keep 16.7% of the variance (`reports/pipeline-runs.jsonl`). The UMAP build stays on the server; switching is one link and a restart ([`hostinger.md`](hostinger.md)).

The limit on throughput was the CPU side of the Ollama server, not the GPU (45 to 47% busy): six servers on the one GPU gave 131 texts per second where one gave 94 to 98. The vector check against the laptop passed (table in section 2).

**Why a GPU instance and not their hosted API.** The build key requires these exact weights; a hosted model that is not the same tag would break the match with the live server.

**Not done yet.** The summary link in Verda's Discord channel. The embedding model comparison as a second use of the compute.

### 3.3 Gemini API

**How it is done.** `pipelines/zones/naming.py`: for each zone, the model gets the zone's distinctive words and sample posts, and returns a short plain name as JSON parsed into a typed model. Temperature 0; the model id and the prompt version (`zone-name-v1`) are stored with each answer; answers are cached on a content hash; a malformed answer keeps the word name and `named: false`. The call goes through the Hostinger AI Router, so the same call counts for the Hostinger criterion. The 48 zones of the live build were named in 98 s, all 48 answers valid (`reports/pipeline-runs.jsonl`); two zones that received the same name are told apart by a distinctive word. The names are what the legend, the tooltips and the search show, for example "Local Crime and Police Reports" or "Criticism of Democrats and Media".

**Model ids.** The Router's model list holds several Gemini ids (among them `gemini-3.5-flash`, `gemini-3.8-flash`, regional variants) and `gemma-4-31b`. A key from Google AI Studio is also in `.env` in case Google wants direct calls.

**Not done yet.** The technique pass (name, plain explanation, quoted span checked against the text) and its evaluation against one other Router model: the main use, after the first probe. Whether a call routed through Hostinger counts for Google's challenge is still to ask at their booth.

### 3.4 Context.dev

**Endpoint used and why** (the note their brief asks for). One endpoint: `POST https://api.context.dev/v1/web/scrape`, with the Markdown format and main content only. It is in the core flow: a link pasted in the paste box is read live through it, the title and the start of the page are embedded with the map's model, and the page lands on the map as a point tied to the posts it resembles most. The panel shows the page title, its address and when it was read. Why this endpoint: the product needs the clean text of one page, at the moment the user asks, with no scraper of our own to maintain on a 2 vCPU server.

**How it is done.** `backend/web_reader/context_dev.py` wraps the call; `backend/analyze/routes.py` uses it. Pages are cached by address. A page that cannot be read, or a failed output inside a 200 answer, gives `not enough evidence` with the reason. The route is rate-limited per client. A first read of a news page took 2.7 s end to end on the live server.

**Not done yet.** Verdicts on the page text (no detector yet): today the page is placed, not judged. Reading the links a swarm shares most.

**To check.** The API reported about 1,000 credits left after a few calls, not 50,000: the `JUNCTION26` code may not be applied.

### 3.5 CRACI

**How it is done.** `.github/workflows/ci.yml`, three jobs, all `runs-on: craci`: Python checks (ruff, pytest), front-end checks (TypeScript, build), then on `main` the build of the two Docker images, their copy to the VPS over SSH and the start of the stack, followed by a check of the public health route for the commit just deployed. The server never builds. On 14 Nov a run took 16 s, 21 s and 2 min 25 s for the three jobs.

**Not done yet.** Their criteria ask for more than moving the jobs: using the build data. The idea that fits the product is a "what this build contains" block in the Reliability view, read from the CRACI API (SBOM of the deployed commit). Not started.

## 4. The checks of the plan (§6)

| # | Check | State |
| --- | --- | --- |
| 1 | Exact Gemini ids on the AI Router; another embedding model than OpenAI's? | Done: Gemini ids listed; embeddings are OpenAI's only |
| 2 | One real call to the Router with the chosen Gemini id | Done (zone naming) |
| 3 | Google DeepMind booth: does a routed call count? Credits form | Form filled. Question still to ask |
| 4 | Hostinger booth: offline compute on Verda and a hosted scrape API are fine? | Still to ask |
| 5 | EmbeddingGemma on the VPS: latency and memory | Done (table in section 2) |
| 6 | Same texts on Verda and on the VPS give the same vectors | Done (table in section 2) |
| 7 | Verda: credits, which instance, does its hosted API serve Gemma | Credits and instance done (`reports/verda.md`). Hosted API not checked |
| 8 | Context.dev: code, one scrape call | Call done. Credits to check |
| 9 | CRACI: invite code, GitHub App | Done |
