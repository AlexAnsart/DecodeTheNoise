# Research: datasets and detection methods

For the four directions of the brief. Traffic and provenance signals are detailed in [`traffic-and-provenance.md`](traffic-and-provenance.md).

Compiled on 13 Nov 2026 from public sources by a literature search. Three records were then checked directly and are marked **(checked)**. The rest is as reported by the search: open the source before quoting a number in the pitch. What could not be verified is listed at the end.

**Datasets stay out of git** (`data/` is ignored). Several are for research use only: record each licence in `data/MANIFEST.json`.

## 1. Where to start

| Direction | Dataset | Method | Catch |
| --- | --- | --- | --- |
| Spot the swarm | [IRA tweets, FiveThirtyEight](https://github.com/fivethirtyeight/russian-troll-tweets) as positives; humans from [fox8-23](https://doi.org/10.5281/zenodo.8035289) as controls; [MassMove](https://github.com/MassMove/TwitterStateBackedOps) campaigns held out | Co-activity network: same URL, same hashtag, same or near-duplicate text within a short window; filter edges; connected components | No open dataset ships matched organic controls. The false-positive rate will be measured on a mismatched control, and the report must say so |
| Name the technique | [PTC, SemEval-2020 Task 11](https://zenodo.org/records/3952415), plus [SemEval-2021 Task 6](https://github.com/di-dimitrov/SEMEVAL-2021-task6-corpus) | A probe for "any technique" and the frequent classes; an LLM held to a fixed taxonomy, a verbatim quoted span and the right to answer "none" | The best published score is modest (micro-F1 0.62), and LLMs do not beat fine-tuned encoders |
| Clean the traffic | [Web robot detection logs](https://zenodo.org/records/3477932), plus [RBA](https://github.com/das-group/rba-dataset) for login abuse | Sessions, verification of declared bots, IP lists, a small model on session features | 2018, one site, masked IPs. The labels reportedly come from known bot lists, so a model partly relearns those lists |
| Trust the source | [Domain quality ratings](https://github.com/hauselin/domain-quality-ratings), [`news_media_reliability`](https://huggingface.co/datasets/sergioburdisso/news_media_reliability) | Reputation lookup, domain age, popularity rank, cloned text across domains | News domains only. An unlisted domain is "unknown", not "bad" |

## 2. Spot the swarm

### Datasets

| Dataset | Content | Access | Use |
| --- | --- | --- | --- |
| [IRA tweets](https://github.com/fivethirtyeight/russian-troll-tweets) **(checked)** | 2,973,371 tweets from 2,848 handles tied to the Internet Research Agency, 2012 to 2018, mostly 2015 to 2017. Columns include `author`, `content`, `publish_date`, `account_category`, `retweet` and the resolved links. Positives only | Open CSV, nine files. No licence stated | The core corpus. Check the resolution of `publish_date` before relying on a 60-second window |
| [MassMove state-backed operations](https://github.com/MassMove/TwitterStateBackedOps) | 101 CSVs from Twitter's 2020 and 2021 state-linked releases, 12 countries. Positives only | Open, 3.63 GB with media. No licence stated | Leave-one-campaign-out tests |
| [fox8-23](https://doi.org/10.5281/zenodo.8035289) | 1,140 LLM-powered bot accounts and 1,140 humans, up to 200 tweets each | Open, CC BY 4.0, 125 MB | Human controls, and the best open set of LLM bots |
| [Reddit suspicious accounts 2018](https://github.com/ALCC01/reddit-suspicious-accounts) | 944 accounts Reddit attributed to the same agency, with comments and submissions | Open, CC0, under 10 MB | A second platform for the demo |
| `cresci-2017`, `caverlee-2011` in the [Bot Repository](https://botometer.osome.iu.edu/bot-repository/datasets.html) | Genuine accounts and spambots | Academic research only | Human controls. Too easy as a benchmark (section 6) |

Not obtainable this weekend: the info-ops dataset with organic controls ([Seckin et al.](https://zenodo.org/records/14189193), academics only), TwiBot-20 and TwiBot-22 (application by email), and the official X archive (its page returned an error).

### Methods

1. **Co-activity network.** Build bipartite graphs of accounts against traces (URL, hashtag, retweeted post, text), project to account similarity, keep the strongest edges, take components ([Pacheco et al.](https://arxiv.org/abs/2001.05658): top 0.5% of edges, accounts with at least 10 actions).
2. **Temporal synchrony.** Identical content posted within one minute linked 74% of campaign accounts on average and almost none in matched samples of regular users ([Schoch et al.](https://www.nature.com/articles/s41598-022-08404-9)). The [Coordination Network Toolkit](https://github.com/QUT-Digital-Observatory/coordination-network-toolkit) (MIT) implements co-retweet, co-tweet, co-link and text similarity from a CSV: read it for the definitions.
3. **Near-duplicate text.** MinHash or SimHash for copies, embeddings for paraphrase.
4. **Account-creation bursts.** Supporting evidence only: batches also appear organically after big events.
5. **A score, not a verdict.** A statistically significant backbone and a continuous coordination score ([Nizzoli et al.](https://arxiv.org/abs/2008.08370)).

### Keeping false positives down

- **Null models.** Shuffle the bipartite graph to get a p-value per edge (Pacheco et al.); entropy-based null models that discount account activity and post virality ([Caldarelli et al.](https://arxiv.org/abs/1905.12687); package [`bicm`](https://pypi.org/project/bicm/), MIT).
- **Several behaviours at once.** One shared hashtag is nothing; the same text in the same minute plus the same link is evidence.
- **Known traps.** Share-button text creates false matches. Coordination is not automation: fans and activists coordinate. A supervised coordination classifier fell from F1 0.98 to 0.71 out of distribution, mostly through false positives ([Vargas et al.](https://arxiv.org/abs/2005.13466)).

## 3. Name the technique

### Datasets

| Dataset | Content | Access | Use |
| --- | --- | --- | --- |
| [PTC, SemEval-2020 Task 11](https://zenodo.org/records/3952415) **(checked)** | News articles with propaganda spans and 14 technique classes; 371 training articles with 6,128 spans | Open on Zenodo, CC BY 4.0, 1.1 MB. **Gold labels are included for the training set only**: hold out articles from it for testing. The task's own site says academic use | Start here |
| [SemEval-2021 Task 6](https://github.com/di-dimitrov/SEMEVAL-2021-task6-corpus) | 950 memes: text with multi-label techniques and spans; test gold released | Open, research use | Short texts, closer to social posts |
| [LOGIC](https://huggingface.co/datasets/tasksource/logical-fallacy) | 13 fallacy classes, 3,761 rows | Open, licence not stated | Fallacy labels |
| [MAFALDA](https://github.com/ChadiHelwe/MAFALDA) | Fallacies with written explanations | Open, licence not confirmed | Examples of explanations |

Gated: SemEval-2023 Task 3 (23 techniques, 9 languages) and SemEval-2024 Task 4 need a registration that is verified by hand.

### What to expect

| Benchmark | Best published | Source |
| --- | --- | --- |
| SemEval-2020, finding the spans | F1 0.52 | [Task paper](https://ar5iv.labs.arxiv.org/html/2009.02696) |
| SemEval-2020, classifying a given span (14 classes) | Micro-F1 0.62; baseline 0.25 | same |
| SemEval-2023, English, paragraph level (23 classes) | Micro-F1 0.38 to 0.45, macro 0.13 to 0.22 | [Leaderboard](https://propaganda.math.unipd.it/semeval2023task3/leaderboard.php) |

- **LLMs do not win here.** GPT-4 reached F1 0.58 on article-level labels and did not beat fine-tuned RoBERTa ([Sprenkamp et al.](https://arxiv.org/abs/2310.06422)). On spans: 0.16 against 0.67 ([Jose & Greenstadt](https://arxiv.org/abs/2505.13706)).
- **Per class, the spread is wide:** about 0.77 on loaded language, single digits on rare techniques.
- **The annotators themselves agree moderately** (γ about 0.6).
- **The encoder matters:** XLM-R large 0.45, XLM-R base 0.34, mBERT 0.22 micro-F1 on the 2023 task ([KInIT](https://aclanthology.org/2023.semeval-1.86.pdf)). A linear probe on a small embedding model is likely to do worse (an inference, untested).

### What to build

1. A binary probe "contains a technique", plus the four to six frequent classes or the coarse groups. Not all 14.
2. A threshold set on held-out articles.
3. An LLM pass on flagged text only: fixed label list, a verbatim span, "none" allowed. **Reject any answer whose quoted span is not in the text.**
4. Report per class, and show micro and macro F1 side by side: the gap exposes the majority-class bias.

## 4. Clean the traffic and trust the source

Signals, lists and endpoints: [`traffic-and-provenance.md`](traffic-and-provenance.md). Additional datasets:

| Dataset | Content | Access | Use |
| --- | --- | --- | --- |
| [RBA login dataset](https://github.com/das-group/rba-dataset) | Over 33M login attempts with attack-IP and account-takeover flags | Open, CC BY 4.0 | The closest open data for login abuse. Synthesised: its authors warn the values are artificial |
| [Web Bot Detection Dataset](https://m4d.iti.gr/web-bot-detection-dataset/) | Logs and mouse movements; humans, moderate and advanced bots; about 50 human sessions per phase | Terms not confirmed | Small, but the only one with advanced bots |
| [`news_media_reliability`](https://huggingface.co/datasets/sergioburdisso/news_media_reliability) | 5,332 domains: reliable, mixed, unreliable | Open, Apache-2.0 | Clean labels for a source-level check |
| [Domain quality ratings](https://github.com/hauselin/domain-quality-ratings) | 11,520 domains scored 0 to 1 ([paper](https://doi.org/10.1093/pnasnexus/pgad286)) | Open, no formal licence | Reputation lookup |
| [RAID](https://github.com/liamdugan/raid), [MAGE](https://github.com/yafuly/MAGE) | Human and LLM text across domains and generators | Open, licences not confirmed | Calibrating an AI-text threshold, if that signal is kept |

No real, labelled credential-stuffing log was found, and no labelled bot dataset for Bluesky.

## 5. Models and libraries that run on CPU

| Embedding model | Parameters | Dimensions | Licence | Note |
| --- | --- | --- | --- | --- |
| [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) | 118M | 384 | MIT | About 100 languages; the default candidate |
| [paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) | 118M | 384 | Apache-2.0 | Tuned for paraphrase, suits near-duplicate clustering |
| [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | 23M | 384 | Apache-2.0 | English only; the lightest |
| [potion-multilingual-128M](https://huggingface.co/minishlab/potion-multilingual-128M) | 128M | 256 | MIT | Static embeddings (no transformer at inference): the fastest, the least precise |
| [multilingual-e5-base](https://huggingface.co/intfloat/multilingual-e5-base) | 278M | 768 | MIT | Slower |

Sizes on disk and throughput on 2 vCPU were not measured: time one before embedding a corpus.

| Library | Licence | Use |
| --- | --- | --- |
| [datasketch](https://pypi.org/project/datasketch/) | MIT | MinHash LSH |
| [networkx](https://pypi.org/project/networkx/) | BSD-3 | Graphs, components, Louvain communities |
| [faiss-cpu](https://pypi.org/project/faiss-cpu/) | MIT | Nearest neighbours |
| [hdbscan](https://pypi.org/project/hdbscan/) | BSD | Density clustering |
| [bicm](https://pypi.org/project/bicm/) | MIT | Bipartite null model |
| [gliner](https://pypi.org/project/gliner/) | Apache-2.0 | Zero-shot entity recognition |
| [rapidfuzz](https://pypi.org/project/rapidfuzz/), [tldextract](https://pypi.org/project/tldextract/) | MIT, BSD-3 | Fuzzy matching, domain parsing |

**Licence trap:** `igraph` and `leidenalg` are GPL. This repository is MIT: prefer `networkx`.

## 6. Evaluation: what the literature warns about

- **Benchmarks are too easy.** One yes-or-no rule gives 0.98 accuracy on `cresci-2017`; models trained on all datasets but one do little better than chance on the one left out ([Hays et al.](https://arxiv.org/abs/2301.07015)).
- **Detectors that score above 97% break on unseen bot classes** ([Echeverría et al.](https://arxiv.org/abs/1809.09684)). On a hard benchmark the best F1 is about 0.59 (TwiBot-22).
- **A famous bot detector in the wild:** precision 0.59 and recall 0.2 at a strict threshold ([Rauchfleisch & Kaiser](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0241045)); a manual audit of hundreds of accounts it called bots found none ([Gallwitz & Kreil](https://arxiv.org/abs/2207.11474)).
- **AI-text detectors fail out of distribution:** 61% false positives on essays by non-native English writers ([Liang et al.](https://arxiv.org/abs/2304.02819)); at one global threshold, 20 to 33% false positives in some domains ([RAID](https://arxiv.org/abs/2405.07940)).
- **Base rates.** Bots were estimated at 9 to 15% of Twitter accounts ([Varol et al.](https://arxiv.org/abs/1703.03107)). At 80% recall and 5% false-positive rate, precision is 64% when 10% of accounts are bad and 14% when 1% are.

What follows for this project (skill `evaluate-detector` already requires most of it):

1. Split by campaign, botnet or domain, never at random. Show in-distribution and held-out numbers side by side.
2. Report recall at a fixed false-positive rate (1% and 5%), and precision at an assumed prevalence.
3. Name the control set used for the false-positive rate, and say when it is not matched.
4. Hand-audit 50 to 100 flagged items from the live demo. Zero errors in 100 still allows a true error rate of about 3 to 4%.
5. Keep "not enough evidence" as an outcome.

## 7. Not verified

- Counts and scores marked as reported by the search: MassMove, fox8-23, the Reddit set, the RBA and reliability datasets, every benchmark figure in sections 3 and 6.
- Licences not stated or not checked: the IRA tweets, MassMove, RAID, MAGE, LOGIC, MAFALDA, the domain quality ratings.
- Whether the labels of the web-robot dataset come from user-agent and IP lists (seen in a search excerpt only).
- Whether the official X information-operations archive can still be obtained.
- The resolution of `publish_date` in the IRA tweets.
