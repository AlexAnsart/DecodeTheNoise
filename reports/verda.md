# What ran on Verda

One run, on 14 Nov 2026. Every figure below was measured during that run or read from `reports/pipeline-runs.jsonl`; nothing is an estimate unless it says "at its measured rate".

## Result

A map of 120,000 posts (build `ira-120k`) is live on the Hostinger VPS. Its vectors were computed on a Verda GPU instance; the VPS only loads files and embeds one query at a time.

| | |
| --- | --- |
| Instance | `1A100.22V`: 1 x NVIDIA A100 80 GB, 22 vCPU, 120 GB RAM, location FIN-03, pay as you go |
| Image | Ubuntu 24.04 + CUDA 12.9 + Docker |
| Up | 13:49:20 to 14:39:26 UTC, 50 minutes |
| Credits | Balance 200.00 EUR before, 198.17 EUR after: 1.83 EUR |
| Left running | Nothing: the instance and its volume were deleted, and the API lists no instance and no volume |

Why this type: at the time, the on-demand single-GPU types with at least 16 GB that Verda listed as available were `1A100.22V` and a confidential-computing variant of the RTX PRO 6000. The cheaper `1V100.4V` was available as a spot instance only (it can be interrupted, and has 4 vCPU for the layout step).

## Why a GPU instance and not the hosted inference API

The map and the live server must use the same weights. The key that travels with every vector names the model, its digest and its quantisation: `embeddinggemma:300m-qat-q8_0@e84a7acc2394`, served by Ollama. A hosted endpoint serves the weights it chose. Two quantisations of this model are not interchangeable: on the laptop, the 8-bit and BF16 variants gave a mean cosine of 0.981 on 120 texts, and 86% of the 10 nearest neighbours in common. A GPU instance runs the exact file the VPS runs. Whether Verda's hosted API serves EmbeddingGemma was not checked.

## Measures

| Step | Verda `1A100.22V` | Laptop (Snapdragon X, CPU) |
| --- | --- | --- |
| Embed | 134,200 texts in 1,023 s: **131 texts/s** | 2,998 in 143 s: 21 texts/s. 17,891 in 1,282 s: 14 texts/s |
| Layout, UMAP in 3D and in 2D | 120,000 points in 209 s | 18,000 points in 155 s |
| Neighbours, exact, k = 10 | 120,000 points in 75 s | 18,000 points in 4.4 s |
| Zones, k-means and distinctive words | 120,000 points in 5.0 s | 18,000 points in 1.1 s |

- 139,995 posts were sampled; 134,200 texts were new to the cache. All of them are now in the laptop's cache (155,089 vectors of 768 values), so a later build reuses them.
- In the same 1,023 s the laptop embeds 14,300 to 21,400 texts at its measured rates.
- The Hostinger VPS (2 vCPU) embedded 100 texts in 12.1 s. It serves queries; it was never meant to embed a corpus.

## The same vectors on three machines

100 texts already embedded on the laptop were embedded again elsewhere and compared by cosine.

| Machine | 768 values: mean, minimum | 256 values served: mean, minimum |
| --- | --- | --- |
| Verda A100, Ollama on CUDA | 0.99985, 0.99972 | 0.99988, 0.99977 |
| Hostinger VPS, Ollama on CPU | 0.99985, 0.99941 | 0.99988, 0.99955 |

The vectors are not bit-identical (different hardware, and the cache stores 16-bit floats), but a pasted text lands where the corpus says it should. The check is a command: `pipelines.embed.compare`.

## What limited the throughput

- One Ollama server on the A100 gave 94 to 98 texts/s, whatever the batch size (64 to 256) and the number of parallel requests (2 to 16).
- Six Ollama servers on the same GPU behind a local load balancer gave 114 to 125 texts/s in short probes and 131 over the run.
- During the run the GPU was 45 to 47% busy and the 22 vCPU were 98% busy inside the Ollama server processes. The limit was on the CPU side of the server, not the GPU.
- Eight servers were started; six had loaded the model when the run began. Each load took about 80 s while the others were working.

So the 20-minute budget held 134,200 texts, not the 300,000 planned. A faster runtime would mean other weights, hence another key: not done.

## Zone names

48 zones, one call each to `gemini-3.8-flash` through the Hostinger AI Router, 98 s in total, temperature 0, prompt version `zone-name-v1`. The model receives the zone's distinctive words and its 12 most central posts and returns a JSON object parsed into a typed model. 48 of 48 answers were valid. Two zones received the same name; the second one carries a distinctive word in brackets. Answers are cached on a hash of the model and the prompt.

## To run it again on a new corpus

1. Create an instance (`POST /v1/instances`, image `24.04.cuda12.9.docker`) with the team's SSH key.
2. On it: start Ollama 0.40.16 with `--gpus all`, pull `embeddinggemma:300m-qat-q8_0`, check the digest, clone the repository, `uv sync --group pipelines`.
3. `PIPELINE_MACHINE="<type and GPU>"`, then `ingest`, `embed`, `layout`, `neighbours`, `zones`, `pack`.
4. Copy `data/work/<build>` and the embedding cache back, run `pipelines.zones.name` and `pipelines.pack`, copy `data/build/<build>` to the VPS, restart the API.
5. Delete the instance and its volume (`PUT /v1/instances`, action `delete`), and list instances to confirm.

The server's cost does not grow with the corpus beyond the files it loads: with 120,000 points the API container holds 169 MiB.
