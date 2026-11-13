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

Fill in once set up. No secrets.

| | |
| --- | --- |
| VPS IP | |
| Domain | |
| Compose project path on the server | |
| Reverse proxy | |
| Health route | |
