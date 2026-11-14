# Hostinger: what the team gets and how to reach it

Source: the challenge brief (`Challenge.md`) and Hostinger's documentation, read on 13 Nov 2026. Nothing here was tested against the team's account yet. Procedure for deploying: skill `deploy-hostinger`.

## What the team gets (free for one month)

| Resource | Details |
| --- | --- |
| VPS (KVM 2) | 2 vCPU, 8 GB RAM, 100 GB NVMe, 8 TB bandwidth, root access, Docker, a free domain. One-click templates: Ollama, n8n, Node.js, Python |
| AI Router credits | One API key, one shared balance, 150+ models (Anthropic, OpenAI, DeepSeek, Mistral, xAI and more) |
| AI Builder | One-month plan to generate and publish a front end or landing page |
| Connector, API, CLI | Manage and deploy from the editor through MCP |
| Mentors | Minijus Savickas (VPS product), Emilis Strimaitis (innovations, AI agents), at the Hostinger booth |

The hard requirement: the final product runs on Hostinger infrastructure, with a public URL the judges can open.

**How to claim it:** [`event/hostinger-access.md`](event/hostinger-access.md). The team gets a coupon code at the Hostinger booth and orders the KVM 2 plan for one month from the Hermes Agent application page, with "5000 Hostinger AI Credits" (they pay for the AI Router) and "Instant web scraping". Consequences:

- The VPS is created from the Hermes Agent template, not from a template we chose. Check on first login what it runs and which ports it holds before starting our own stack.
- The message does not say how to claim the free domain: ask at the booth.
- What "Instant web scraping" gives (an API, a tool for the agent) was not checked.

## AI Router

| | |
| --- | --- |
| Base URL | `https://router.hostinger.com/v1` |
| Key | Hostinger dashboard → AI Router. Starts with `sk-hstgr-` |
| Formats | OpenAI (`/chat/completions`, `/responses`, `/embeddings`) and Anthropic (`/messages`) |
| Model ids | Dashboard → AI Router → Models. Copy the exact id |
| Limits | Per key: daily and monthly spending limits, and a list of allowed models |

```python
import os

from openai import OpenAI

client = OpenAI(api_key=os.environ["HOSTINGER_ROUTER_API_KEY"], base_url="https://router.hostinger.com/v1")
```

- The embeddings route and the two embedding models (`text-embedding-3-small`, `text-embedding-3-large`) are listed in LiteLLM's provider page for the router, not in Hostinger's own help article. **Check with one real call** before building on it.
- Create one key per use (development, deployed app) so a leak or a runaway loop is contained.

Sources: [Hostinger help article](https://www.hostinger.com/support/what-is-hostinger-ai-router-and-how-to-get-started/), [LiteLLM provider page](https://docs.litellm.ai/docs/providers/hostinger_router).

## MCP server (already configured in this repo)

`.cursor/mcp.json` (Cursor) and `.mcp.json` (Claude Code) register the hosted server `https://mcp.hostinger.com`. Sign-in is OAuth in the browser on first use; no token is stored in the repo.

- Three tools: `search` (find an operation and its input schema), `execute` (run one), `multi-execute` (up to 20 in sequence).
- VPS operations include `vps_docker_*` (Docker Compose projects: list, create, update, logs, restart, stop, delete) and `vps_firewall_*`.
- The Hostinger Connector editor extension is the managed alternative. It disables the VPS product group by default: enable it in the Hostinger sidebar.
- If an API token is ever used instead of OAuth, it goes in an environment variable (`HOSTINGER_API_TOKEN`), never in a committed file.

Sources: [Connector docs](https://docs.hostinger.com/hostinger-connector), [manual configuration](https://docs.hostinger.com/hostinger-connector/manual-configuration), [MCP server repository](https://github.com/hostinger/api-mcp-server), [API reference](https://developers.hostinger.com).

## Constraints that shape the design

- **No GPU, 2 vCPU.** Heavy embedding or training jobs run offline (laptop, or credits from a tech-challenge partner) and ship as files. The server does light inference: dot products, small models, calls to the AI Router.
- **8 GB RAM** shared by the API, the data store, any local model and the reverse proxy.
- **Architecture mismatch.** The VPS is expected to be x86-64 Linux (confirm with `uname -m` on first login). A laptop on ARM64 Windows cannot build its images directly: build on the server or in CI.
- **One month free.** Winning teams get a year of hosting.

## Deployment record

Set up on 14 Nov 2026. No secrets.

| | |
| --- | --- |
| VPS | KVM 2, id 2160938, `srv2160938.hstgr.cloud`, x86-64, Ubuntu 24.04 with Docker and Traefik (template of the Hermes Agent application) |
| VPS IP | 153.92.223.45 |
| Public URL | `https://noisemap.srv2160938.hstgr.cloud`. Every subdomain of the server's host name resolves to it; no domain was claimed yet |
| Compose project path on the server | `/docker/noisemap` (a clone of this repository; `.env` and `data/build/` live there and are not in git) |
| Reverse proxy | The Traefik container Hostinger installs (`/docker/traefik`, host network, ports 80 and 443, Let's Encrypt by HTTP challenge). Our services are published by labels in `deploy/docker-compose.yml` |
| Health route | `/api/health` returns the commit and the map build being served |
| Map build served | The folder `data/build/current` points to. On the server today: `ira-120k` (UMAP layout, the one served) and `ira-120k-pca` (PCA layout, served for an hour on 14 Nov as a test), same posts, vectors, neighbours and zones. To switch: `ln -sfn <build> data/build/current` in `/docker/noisemap`, then `docker compose --project-directory . -f deploy/docker-compose.yml restart api`. A deploy does not change it |
| Deploy | Push to `main`: the CI builds the images on CRACI and loads them on the server (`.github/workflows/ci.yml`, `deploy/up.sh`) |
| Workspaces | `/docker/noisemap/data/workspaces` on the server, mounted in the API container and written by it: one folder per workspace, `accounts.sqlite` (hashed keys, settings, daily usage), `embeddings.sqlite` (vectors already computed, by text), `.numba` (compiled layout code). Not in git and not in an image: a redeploy keeps it |
| Server `.env` | `LLM_MODEL=gemini-3.8-flash` added on 15 Nov 2026: without it the server names no zone and reviews nothing |
| Also on the server | Hermes Agent (`/docker/hermes-agent-yciq`), left as installed |
| Firewall | Hostinger firewall group `noisemap` (id 401111), active on the VPS: TCP 22, 80 and 443 from anywhere, everything else dropped. Hermes Agent is still reachable through Traefik, no longer on its direct port |

## Measured on the server

Night of 14 to 15 Nov 2026, commit `5c7bb8b`, from outside over HTTPS, with a script that plays the whole API (not in the repository). The server was otherwise idle. A fresh text is one it never embedded.

| What | Measured |
| --- | --- |
| One post sent (`POST /api/v1/items`), fresh text | 0.17 to 0.38 s |
| The same text sent again | 0.06 s: the vector comes from the cache |
| A batch of 200 fresh posts, from received to placed on the map | 25.6 s, 7.8 posts a second |
| While that batch is embedded: a search by meaning on the demo map, one post sent | 0.72 s, 0.55 s |
| Layout, zones and words of a workspace of 20, 101 and 205 points | 0.5 s, 0.7 s, 0.4 s |
| Memory of the API container (with its computing process), of Ollama | 679 MiB, 493 to 729 MiB |
| Model alone, chunks of 8 against 16 texts a call (64 fresh texts, twice each) | 7.3 and 8.8 against 8.5 and 9.0 posts a second |

What these measures decided:

- **1,000 posts per workspace and per batch.** At 8 posts a second, a thousand posts take about two minutes; ten thousand would take twenty.
- **Chunks of 8 texts.** The model takes one call at a time, so a search or a single post waits for the chunk in flight. Halving the chunk costs little speed and halves that wait.
- **Ollama weighs eight times the other containers (`cpu_shares`).** While UMAP compiled in the API container, posts were embedded at 1 a second and a search took 7 s: Docker shares the processor between containers by weight, whatever the priority of a process inside one. With the weight, the embedding kept 6 to 7 posts a second during a compilation.
- **Layouts run in a process of their own, one at a time.** A refresh that started during the start-up compilation got corrupted neighbour indices from the compiled code under UMAP, and compiling inside the API process slowed every request.
- **The first start compiles for about 80 s; later ones do not.** The compiled code is kept in `.numba` on the volume: after the second deploy, the first refresh took 0.5 s.

Before a push that changes an image, build it on the server from the committed tree, with the ignore file: `git archive HEAD .dockerignore pyproject.toml uv.lock backend pipelines probes reports deploy | ssh root@<server> 'tar -x -C /tmp/x && docker build -f /tmp/x/deploy/api.Dockerfile /tmp/x'`. A first deploy failed in the CI on a folder the ignore file left out, which a build without that file had not shown.
