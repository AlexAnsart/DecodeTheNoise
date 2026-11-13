# DecodeTheNoise

Telling signal from noise on the web, with the evidence shown. An entry to the Hostinger challenge "Decode the Noise" at [Junction 2026](https://2026.hackjunction.com/) (Espoo, 13 to 15 November 2026).

**Status:** project set up, no product code yet. Live URL: to come.

## The challenge

Build a deployed, working system that detects one or more of: coordinated inauthentic behaviour, propaganda techniques in text, automated traffic in server logs, or the trustworthiness of a source. It must run on Hostinger infrastructure and report honest precision and false-positive rates. Full brief: [`docs/Challenge.md`](docs/Challenge.md).

## Repository

| Path | Content |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Instructions for coding agents (Cursor, Claude Code) and the project's engineering rules |
| [`docs/strategy.md`](docs/strategy.md) | Ideas, directions, open decisions, timeline |
| [`docs/hackathon.md`](docs/hackathon.md) | Deadlines, rules, submission checklist, judging |
| [`docs/research/`](docs/research/) | Datasets, methods and published results for each direction |
| [`docs/hostinger.md`](docs/hostinger.md) | VPS, AI Router, MCP server |
| [`docs/tech-challenges/`](docs/tech-challenges/) | Partner tech challenges that can be combined with the main one |

Agent skills and editor rules (`.claude/`, `.cursor/`) are kept on the team's machines and are not part of this repository.

## Setup

```
cp .env.example .env    # then fill in the Hostinger AI Router key
```

The Hostinger MCP server is registered in `.mcp.json`; it asks for sign-in on first use.

## Licence

[MIT](LICENSE). All code in this repository was written during the event.
