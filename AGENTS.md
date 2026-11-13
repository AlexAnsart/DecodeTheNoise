# AGENTS.md

Instructions for coding agents (Cursor, Claude Code) working on DecodeTheNoise. `CLAUDE.md` imports this file: edit this one.

## 1. The project

DecodeTheNoise is an entry to the Hostinger challenge at Junction 2026 (Espoo, 13 to 15 Nov 2026): a deployed, working system that tells signal from noise on the web, and shows its evidence.

The brief (`docs/Challenge.md`) gives four directions. Depth in one or two beats shallow coverage of all four.

| Direction | What it detects |
| --- | --- |
| Spot the swarm | Coordinated inauthentic behaviour: timing, phrasing and interaction patterns across accounts |
| Name the technique | Propaganda techniques in a text, each one named and explained to the reader |
| Clean the traffic | Human, declared bot and stealth AI agent in real server logs |
| Trust the source | A credibility or provenance signal for web content, with its limits stated |

Current thinking, open decisions and the plan: `docs/strategy.md`.

## 2. Hard constraints

1. **Final submission: Sunday 15 Nov 2026, 10:00 Helsinki time (UTC+2).** Nothing late is accepted. Deadlines, rules and the submission checklist: `docs/hackathon.md`.
2. **Live on Hostinger.** The product runs on the team's Hostinger VPS at a public URL the judges can open. Something that only runs on a laptop does not count.
3. **All code in this repository is written during the event.** Junction disqualifies projects that ship code written before it, apart from open-source libraries. Never paste code from an earlier or private project. Open-source dependencies are fine: declare them.
4. **MIT licence, public source.** Nothing proprietary, nothing secret, no dataset whose licence forbids redistribution goes into git.
5. **Measured, not claimed.** Every detector has precision and false-positive rate measured on held-out data (skill `evaluate-detector`). A number that was not measured is not written anywhere.
6. **Evidence with every verdict.** The product never shows a score alone. It shows what was found, where, and how reliable that detector has measured to be.

## 3. What wins

| Criterion | Weight | What it means for the work |
| --- | --- | --- |
| Detection quality: accuracy, false-positive handling, explainability | 40% | Honest metrics on real data, a visible answer to "what happens when it is wrong", evidence the user can read |
| Technical execution and live deployment on Hostinger | 25% | Deployed early, stable under the demo, uses the platform (VPS, AI Router) |
| Originality and real-world impact | 20% | One idea the other teams do not have, tied to a real user |
| Demo clarity | 15% | A 2-minute video and a URL that explain themselves |

When two tasks compete, the one that moves the larger weight goes first. The judges said it plainly: detection logic over a polished front end.

## 4. How to work

- **Think before coding.** State the assumption you are making. If the request has two readings, say both and pick, or ask. If a simpler approach exists, say so before building the complex one.
- **Simplicity first.** The least code that solves the problem. No feature that was not asked for, no abstraction for a single use, no configuration nobody needs, no handling for cases that cannot happen. If 200 lines could be 50, rewrite.
- **Surgical changes.** Touch what the task needs. Do not reformat, rename or "improve" neighbouring code. Match the existing style. Remove what your change made unused; leave older dead code alone and mention it.
- **Goal-driven.** Turn the task into a check that can pass or fail, then loop until it passes. "Fix the bug" becomes "write the case that reproduces it, then make it pass".
- **Verify before saying done.** Run the checks (§9). Open the page or call the endpoint. A claim of "works" names what was run.
- **Hackathon time.** Prefer a working end-to-end slice today over a perfect layer. Cut scope, not honesty: a missing feature is fine, a faked number is not.
- **Delegate bulk work.** Labelling, scraping, mechanical edits and wide searches go to subagents or batch scripts, in parallel.

## 5. Repository rules

- **Never discard work you did not write in this conversation.** Other agents and teammates work in the same tree. No `git checkout -- .`, `git restore`, `git reset --hard`, `git clean`, `git stash` on files you did not touch, unless Alexandre says so.
- **No push, no force-push, no history rewrite without an explicit yes.** Commit only when asked (skill `commit`).
- **No new branch or worktree unless asked.** Work on the current branch.
- **Secrets never enter git, the chat or a log.** Keys live in `.env` (ignored). `.env.example` lists the names.
- **`data/`, `models/`, `demos/`, `.local/`, `docs/sensitive/`, `.claude/` and `.cursor/` are git-ignored.** Never force-add them. Skills, editor rules and the demo video workspace therefore exist only on a team member's machine.
- **Skills live in `.claude/skills/<name>/SKILL.md` only.** Cursor and Claude Code both read that folder. Do not duplicate a skill elsewhere.
- **Documentation is short.** Do not create a markdown file nobody asked for. Update the existing one.

## 6. Talking to Alexandre

- Reply in the language he writes in (usually French). Everything written to the repository is English: code, comments, logs, commit messages, documentation, UI text.
- Lead with the result or the decision needed. Short sentences, plain words, no filler.
- Say what was verified and what was not. If unsure, say "unsure" and what would settle it.
- Contradict him when the evidence does: he asked for it. Give the reason and the alternative in one or two lines.
- Propose the next step when one is obvious.

## 7. Stack and layout

**Default, not locked.** Confirm with Alexandre before the first scaffold; once code exists, the code is the truth and this section is updated.

| Part | Default | Why |
| --- | --- | --- |
| Backend | Python 3.12, FastAPI, managed with `uv` | The data-science stack lives in Python |
| Detection | numpy, scikit-learn, networkx | Linear probes and graph statistics run on 2 vCPU. No GPL dependency (`igraph`, `leidenalg`): the repository is MIT |
| Embeddings and LLM | Hostinger AI Router (OpenAI-compatible) | One key, team credits, counts toward the Hostinger criterion |
| Storage | SQLite, plus numpy or parquet files for vectors | One file, no server to run in 8 GB |
| Front end | React, TypeScript, Vite | Fast to build; canvas or WebGL for clouds and graphs |
| Deploy | Docker Compose on the VPS, reverse proxy with TLS | Skill `deploy-hostinger` |

```
backend/      API and detectors, one folder per feature
frontend/     Web app, one folder per feature
pipelines/    Offline jobs: ingest, embed, train, evaluate
data/         Datasets, vectors, runs (git-ignored)
demos/        Demo video workspace: recording engine, takes, audio (git-ignored)
reports/      Evaluation reports and metrics.json (committed)
deploy/       Compose file, proxy configuration
docs/         Brief, hackathon facts, strategy, research, tech challenges
```

The dev laptop is Windows on ARM64 without Docker; the VPS is x86-64 Linux. Build images on the server or in CI. If a Python wheel is missing for ARM64 Windows, say so and use an x64 interpreter or the server rather than working around it silently.

## 8. Vocabulary

Use these words in code, UI and documentation. One word per concept.

| Term | Meaning |
| --- | --- |
| Item | One unit of content or traffic: a post, an article, a request, a session |
| Actor | Whoever is behind items: an account, a client, a domain |
| Signal | One measurable observation about an item or an actor |
| Probe | A small linear classifier on an embedding vector |
| Verdict | A label, a confidence level, the evidence, and the measured reliability of the detector |
| Swarm | A set of actors whose behaviour is coordinated beyond what chance explains |

Confidence levels are `possible`, `probable` and `not enough evidence`. The product never states that someone is a bot or that a text is propaganda as a fact.

## 9. Code

Language rules are in `.cursor/rules/python.mdc` and `.cursor/rules/typescript.mdc`. Cursor attaches them by file type. **Claude Code: read the matching file before editing Python or TypeScript.**

For every language:

- **One responsibility per file.** Beyond about 150 lines, or a second responsibility, split.
- **Folders by feature, not by type.** `swarm/`, `techniques/`, `traffic/`, `provenance/`. No `utils/` or `helpers/` dumping ground.
- **Types at the boundaries.** Parse and validate what comes from outside (HTTP, files, LLM output, datasets) once, where it enters. Inside, trust the types. No handling for states that cannot occur.
- **One definition per type and per constant.** Do not duplicate a schema between modules; the API schema is the contract between backend and front end.
- **Names say what the thing is.** Python: `snake_case`, classes `PascalCase`. TypeScript: components `PascalCase.tsx`, hooks `useSomething.ts`, constants `UPPER_SNAKE_CASE`.
- **Comments explain why, never what.** No commented-out code.
- **No sleep or polling where an event exists.** No hidden global state.
- **A logger, not `print` or `console.log`.**
- **Reproducible.** Fixed seeds, pinned dependencies, lockfiles committed. Each dataset has a line in `data/MANIFEST.json` (source, licence, date, hash) and a script that fetches it.

Checks, to run before saying a change is done (once the scaffold exists; update this list when it does):

```
uv run ruff check . && uv run ruff format --check . && uv run pytest     # backend, pipelines
npx tsc --noEmit && npm run build                                        # frontend
```

## 10. Detection rules

- **Split by group, never by row** (account, thread, campaign, source, near-duplicate cluster), and by time when there are timestamps. Leakage is the commonest way to a wrong number.
- **Report at realistic base rates.** A detector at 2% false-positive rate is mostly wrong when 1% of items are positive. Say what precision becomes.
- **Three outcomes, not two.** Flagged, not flagged, not enough evidence. Short texts, new accounts and thin sessions abstain.
- **A probe flags; it does not convict.** Cheap detectors rank and filter. The LLM pass and the evidence view come after, on what was flagged.
- **LLM steps are pinned and cached.** Model id, prompt version and temperature are recorded; outputs are parsed into a typed schema; quoted evidence is checked to exist in the source text.
- **Coordination is behaviour, not opinion.** The swarm detector looks at timing, duplication and interaction structure. Sharing a view is not coordination; a null model sets the bar.
- **The embedding model's key travels with every vector and every probe.** A probe is never applied to vectors from another model or dimension.
- **Privacy.** IP addresses and account identifiers from real data are hashed or truncated before they reach the UI or a commit.

Method and procedure: skills `probe-engineering` and `evaluate-detector`.

## 11. Performance

The server has 2 vCPU, 8 GB of RAM and no GPU.

- Heavy work (embedding a corpus, training, graph layout, dimension reduction) runs offline in `pipelines/` and ships as files. The server loads them.
- Online work stays light: dot products, lookups, one LLM call for a flagged item. Load models and files once at start-up.
- Say the expected cost of anything in a hot path (items per second, memory) before building it, and measure after.
- Cache every paid call (embedding, LLM) on a content hash. The AI Router balance is shared and finite.
- The browser renders large clouds and graphs on canvas or WebGL and never receives more data than it draws.

## 12. Where to read more

| Need | Read |
| --- | --- |
| The brief | `docs/Challenge.md` |
| Deadlines, rules, submission checklist, judging | `docs/hackathon.md` |
| Ideas, directions, open decisions | `docs/strategy.md` |
| Datasets, methods, prior work | `docs/research/` |
| Hostinger VPS, AI Router, MCP | `docs/hostinger.md` |
| Tech challenges that can be combined with this one | `docs/tech-challenges/` |
| Train or improve a probe | skill `probe-engineering` |
| Measure a detector, write its report | skill `evaluate-detector` |
| Deploy, check the live site | skill `deploy-hostinger` |
| Commit | skill `commit` |
| Resolve a merge conflict | skill `mergeconflict` |
| Build the pitch deck | skill `frontend-slides` |
| Produce the 2-minute demo video | skill `produce-video` (stages: `demo-setup`, `narrate`, `film-demo`, `sync-narration`) |

## 13. Private notes

`.local/` is git-ignored and holds private reference notes that exist only on a team member's machine. **If `.local/README.md` exists, read it at the start of any task**: it points to earlier work worth studying and states the policy for using it. Its content never goes into a commit, and §2.3 always applies.
