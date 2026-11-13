# Tech challenges

Partner challenges for the best use of a technology. They run alongside the main challenge: one project can be submitted to the Hostinger challenge and to one or more of these.

Source: [hackjunction.app/participate/45/challenges](https://hackjunction.app/participate/45/challenges).

## Status: incomplete

**Only CRACI is here.** The challenges page sits behind the Junction sign-in, so it could not be read automatically on 13 Nov. The other tech challenges are missing until someone signed in opens the page for the scrape. Nothing below was guessed.

| Challenge | File | Fit with DecodeTheNoise |
| --- | --- | --- |
| Best use of CRACI | [`craci.md`](craci.md) | Good, low cost. See below |

## CRACI: fit

What it asks: the project's CI/CD runs on CRACI (`runs-on: craci` in a GitHub Actions job). The winning entries do something bold with the build data (SBOMs, provenance, AI fixes), not just run CI there.

What it gives this project, whatever the prize:

- **x86-64 Linux builds.** The dev laptop is ARM64 Windows without Docker. A CRACI job can build and test the images the VPS will run.
- **Compute.** 1,000 € of credits, usable "for CI/CD or any compute need", on runners of up to 32 vCPU and 96 GB of RAM. The offline pipeline (embedding the corpus, training probes, graph layout) can run there as a workflow instead of on the 2 vCPU server.

Cost: about ten minutes of setup, plus one workflow file. The invite code comes from the `#craci` Discord channel or the CRACI booth.

To be a credible entry rather than a checkbox, the build data has to appear in the product. One idea that fits the theme: apply "Trust the source" to the detector itself, with a provenance page that shows what each deployed build contains (its SBOM, read from the CRACI API). Decide after the main pipeline works.

## Adding a challenge

One file per challenge, named after the partner in lower case (`craci.md`). Keep the partner's text as published, then add a line to the table above with an honest fit: what it would cost, what it would bring.
