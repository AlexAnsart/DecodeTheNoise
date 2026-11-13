# Strategy

Working notes: ideas, how they map to the brief, what is still open. Update as decisions are made; delete what is no longer true.

## Starting ideas (Alexandre, 13 Nov)

**Basics**

- Detect mass content coming from the same identifiers, IP addresses or locations.
- Account for VPNs. Link sources to each other.
- Read the research on CAPTCHAs and bot detection.

**What should set the project apart**

- Embed all content semantically, not a sample.
- Train light probes on the vectors to sort content by kind: spam, bot-like, money request, political, and so on.
- Run an LLM over what the probes flag, to name the technique: loaded language, fear appeal, whataboutism, fabricated authority.
- Define precisely what counts as propaganda.
- Relational graphs, flows, tracking of mass behaviour.
- Heavy use of NLP, including entity detection.

## How the ideas map to the four directions

| Direction | Ideas that serve it | Data it needs |
| --- | --- | --- |
| Spot the swarm | Embeddings for near-duplicate and same-narrative detection, relational graph, timing | Posts with account, timestamp and interaction fields, plus known coordinated campaigns as ground truth |
| Name the technique | Probes as a cheap first filter, LLM pass with quoted evidence, a written definition of each technique | Texts annotated with techniques at span level |
| Clean the traffic | Same IP or identifier, VPN and datacentre ranges, bot-detection research | Server logs with ground truth for human, declared bot and stealth agent |
| Trust the source | Entity detection, linking sources, aggregation of the other signals per domain | A reference list of source reliability |

## Assessment

What holds up:

- **The cascade is the right architecture for this server.** Embed once, score with dot products, spend LLM calls only on what was flagged. It is cheap on 2 vCPU, and each stage can be measured separately, which is what 40% of the judging rewards.
- **The semantic layer joins two directions.** The same vectors give narrative clusters (swarm) and probe scores (technique), so "Spot the swarm" and "Name the technique" can share one pipeline and one evidence view.

What does not, or needs a decision:

- **IP addresses do not exist in public social-media datasets.** "Same IP, same location, VPN" is evidence for the traffic direction only. For swarms, the available signals are timing, text duplication, shared links and interaction structure.
- **Probes need labels.** With about 36 hours, expect two to four probes with honest metrics, not ten. Each one costs labelling, an error audit and an evaluation report. Pick the classes that the demo needs.
- **"Propaganda" has to be operational.** Use a published taxonomy of techniques with span-level annotations rather than inventing one: the definitions and the test set come for free, and the numbers are comparable to published results.
- **Naming techniques will score modestly, and an LLM does not fix that.** The best published result on the standard corpus is micro-F1 0.62 with fine-tuned encoders; GPT-4 did not beat them, and did far worse at locating spans. Plan for a few frequent classes, a quoted span that is checked against the text, and "none" as a valid answer. Technique naming is strongest as the explanation of something already flagged, not as a classifier judged on its own (`research/datasets-and-methods.md` §3).
- **No open coordination dataset comes with matched organic accounts.** The known campaigns are positives only. The false-positive rate of a swarm detector will be measured on controls from another dataset, or with a null model, and the report has to say so.
- **CAPTCHA research says challenges no longer separate humans from bots.** Solvers pass deployed CAPTCHAs as well as or better than people (`research/traffic-and-provenance.md` §5). The useful lesson is the opposite of building one: score behaviour and network evidence, and keep a challenge for the uncertain band.
- **VPN and datacentre detection is partial by nature.** It rests on IP-range lists that are incomplete and age quickly, and per-IP evidence does not survive residential proxies (one study found 2.2% of 6.18M proxy IPs on blacklists). State it as a signal with a known miss rate, never as proof.
- **The embedding model is chosen once.** A probe only works on vectors from the model it was trained on, and a multi-gigabyte local model will not serve a 2 vCPU, 8 GB machine. The choice is between hosted embeddings through the AI Router and a small local model (decision 4).
- **Four directions in one weekend is shallow.** The brief says depth in one or two wins.

## Proposed shape (to challenge)

1. **Primary: the swarm, explained by its techniques.** Coordination evidence first (same text, same link, same minute, graph structure, tested against a null model), then narrative clusters from embeddings, then the techniques named on the swarm's messages with quoted spans. One evidence card per swarm, with measured reliability. Corpus to start: the 3 million tweets of a known state operation as positives, an open set of human accounts as controls, other campaigns held out.
2. **Stretch, or a serious alternative: traffic.** It is the closest to Hostinger's own business ("hosting itself will have to evolve to tell signal from noise by default"), and it has the shortest path to honest numbers:
   - a labelled public dataset of sessions with ready-made features (4 million requests, CC BY 4.0), so a first session classifier can be trained and measured without parsing raw logs;
   - three cheap signals with near-certain labels: declared crawlers verified against published IP ranges, the network class of the IP, and a scanner rule;
   - the product's own access logs on the VPS as live, current traffic for the demo.

   Its weak points: that dataset is from 2018 with masked IPs, and its labels reportedly come from known bot lists (not verified), so a model trained on it partly relearns those lists. The "stealth AI agent" class has no public ground truth: it would have to come from traffic the team generates and labels itself. Details: `research/traffic-and-provenance.md`.
3. **By-product: source trust.** Aggregating swarm and technique signals per domain gives a provenance signal without a separate pipeline. Ship it only if its limits can be stated honestly.

This is a proposal. The direction is Alexandre's call.

## Open decisions

| # | Decision | Options | Needed by |
| --- | --- | --- | --- |
| 1 | Primary direction(s) | Swarm plus technique; traffic first; another pairing | Friday night (preliminary submission) |
| 2 | Who the user is | Trust-and-safety analyst; journalist or researcher; site owner on a hosting platform | Before the UI |
| 3 | Stack | Default (Python and FastAPI, React and Vite, SQLite), or another | Before the scaffold |
| 4 | Embedding model | AI Router embeddings (endpoint to verify, spends credits, no RAM cost) or a small local model on CPU such as `multilingual-e5-small` (free, uses server RAM, speed on 2 vCPU to measure, wheels to check on ARM64) | Before embedding the corpus. One model for batch and live |
| 5 | Datasets | Starting picks per direction in `research/datasets-and-methods.md` §1 | Saturday morning |
| 6 | Which probes | Two to four classes the demo needs | After the corpus is chosen |
| 7 | Tech challenges to combine | See `tech-challenges/` | Saturday midday |
| 8 | Team and roles | Solo, or up to four | Now |

## Timeline (Helsinki time)

| When | Goal |
| --- | --- |
| Fri night | Direction and corpus chosen. Preliminary submission before 23:59. Scaffold. A hello-world deployed on the VPS behind the domain |
| Sat morning | Corpus ingested and embedded. First detector with a baseline and a first evaluation report |
| Sat 13:00 | Hostinger keynote: listen for what the jury cares about |
| Sat afternoon | Second detector or the LLM pass. The evidence view |
| Sat evening | Evaluation reports, false-positive audit, the metrics page. Redeploy |
| Sat night | Demo scenario on real data. Record the video. Pitch deck |
| Sun 09:00 | Freeze. Submit as FINAL, with video, deck, URL and source link, before 10:00 |
| Sun 10:30 | Peer review at the table |

## Risks

| Risk | Mitigation |
| --- | --- |
| The first deploy fails on Sunday morning | Deploy a skeleton on Friday night or Saturday morning, redeploy at every milestone |
| No usable ground truth for a direction | Check the dataset before committing to the direction; fall back to injected synthetic campaigns for coordination |
| Numbers look good because of leakage | Group and time splits, skill `evaluate-detector` |
| AI Router credits run out | Cache on content hash, cap tokens, a spending limit per key |
| The demo depends on a live LLM call that times out | Precompute and cache the demo scenario; live calls are a bonus |
| The laptop (ARM64 Windows, no Docker) cannot build or run part of the stack | Build on the VPS or in CI; run heavy jobs on the server or a partner's credits |
