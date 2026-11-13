# Research: traffic, linking sources, provenance

For the directions "Clean the traffic" and "Trust the source", and for linking sources to each other.

Compiled on 13 Nov 2026 from public sources by a literature search. Build times, false-positive risks and mitigations are estimates, not sourced. Papers dated 2026 and vendor figures were not cross-checked: open the source before quoting one in the pitch. What could not be verified is listed at the end.

"Plain logs" means the nginx or Apache combined format: IP, time, request line, status, bytes, referrer, user agent.

## 1. Shortlist for a 2 vCPU server

Ranked by detection value per hour of work.

| # | Signal | Why | Build | False-positive risk | Mitigation |
| --- | --- | --- | --- | --- | --- |
| 1 | **Declared-bot verification.** The user agent claims Googlebot, Bingbot or GPTBot; check it against the published IP ranges or forward-confirmed reverse DNS | Near-certain labels both ways. On honeypot sites, Googlebot claims that failed verification were malicious ([Li et al., IEEE S&P 2021](https://www.securitee.org/files/goodbotbadbot_oakland2021.pdf)) | 2 to 3 h | Stale range files, DNS timeouts | Refresh daily; a DNS failure is "unknown", not "fake" |
| 2 | **Network class of the IP:** ASN, hosting, VPN, Tor, privacy relay | Cheap offline join. OWASP recommends telling residential from hosting ([cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html)) | 2 to 3 h | VPN users, corporate gateways, iCloud Private Relay | A score weight, never a verdict. Label VPN and relay apart from hosting |
| 3 | **Scanner rule:** many distinct paths answering 400, 403 or 404 | A proven open rule ([CrowdSec http-probing](https://raw.githubusercontent.com/crowdsecurity/hub/master/scenarios/crowdsecurity/http-probing.yaml)) | 1 to 2 h | Broken links after a migration | Count distinct paths; ignore requests referred by the site itself |
| 4 | **Session behaviour model:** rate, error ratio, HEAD ratio, empty referrer, robots.txt, asset-to-page ratio, timing variance | The most studied approach, and a labelled dataset exists (section 3) | 6 to 10 h | Shared NAT, text browsers and screen readers, uptime monitors | Session key is IP plus user agent; ratios not counts; drop sessions under 3 requests; threshold at a stated false-positive rate |
| 5 | **Login abuse at three levels:** per IP, per subnet or ASN, site-wide | Credential stuffing spreads over proxies, so per-IP limits miss it | 4 h | Forgotten passwords, office NAT | Report a site-wide spike as a campaign, not as per-IP blocks |
| 6 | **Cross-IP campaign clustering:** same path sequence, synchronised timing, shared ASN | Links sources without trusting the IP, in the style of [DeBot](https://www.cs.unm.edu/~chavoshi/debot/SocInfo.pdf) and [Pacheco et al.](https://arxiv.org/abs/2001.05658) | 6 to 8 h | A viral link produces a real crowd | Require two independent matching dimensions; never link on user agent alone |
| 7 | **TLS fingerprint (JA4) against the claimed browser** | 86.2% of clients claiming Chrome or Firefox were not (Li et al.) | 3 to 5 h, needs a patched nginx | Antivirus or corporate TLS interception | Mismatch evidence only, combined with another signal |
| 8 | **Provenance score** (section 6) | Free endpoints | 4 to 6 h | New legitimate sites | Evidence per signal; "unknown" kept apart from "bad" |

## 2. What each linking signal can and cannot do

| Signal | In plain logs? | Holds against evasion? | Reference |
| --- | --- | --- | --- |
| IP and subnet | Yes | Weak. Residential proxies: 6.18M IPs across 52,905 ISPs, 2.2% on blacklists. Noisy: over 90% of cellular networks use carrier-grade NAT | [Mi et al. 2019](https://xianghang.me/files/resi_paper.pdf), [Richter et al. 2016](https://arxiv.org/abs/1605.05606) |
| ASN and hosting class | Yes, offline join | Good against datacentre bots and commercial VPNs; blind to residential proxies | [IPinfo Lite](https://ipinfo.io/developers/ipinfo-lite-database), [X4BNet](https://github.com/X4BNet/lists_vpn) |
| VPN, proxy and Tor lists | Yes, offline join | Tor: official list. VPN lists are incomplete by their own admission. Apple says to treat Private Relay like carrier-grade NAT | [Tor](https://blog.torproject.org/changes-tor-exit-list-service/), [Apple](https://developer.apple.com/icloud/prepare-your-network-for-icloud-private-relay/) |
| TLS fingerprint (JA3, JA4) | No: needs the TLS-terminating server | Survives IP rotation. Identifies the client software, not the operator | [JA4](https://github.com/FoxIO-LLC/ja4), [Cloudflare](https://developers.cloudflare.com/bots/additional-configurations/ja3-ja4-fingerprint/) |
| HTTP/2 fingerprint, header order | No: needs the server edge | Same as TLS | [Akamai, Black Hat EU 2017](https://blackhat.com/docs/eu-17/materials/eu-17-Shuster-Passive-Fingerprinting-Of-HTTP2-Clients-wp.pdf) |
| Browser or device fingerprint | No: needs client JavaScript | Evasive bots beat a commercial detector 52.93% of the time; inconsistency rules cut that by about half | [FP-Inconsistent](https://arxiv.org/abs/2406.07647) |
| TCP against TLS round-trip gap | No: needs packet timing | Targets residential proxies: a gap over 50 ms flags a proxied connection | [BADPASS](https://www.eurecom.edu/publication/7056/download/sec-publi-7056.pdf) |
| Timing and behaviour | Yes | Survives IP rotation when the operator reuses a script. DeBot reports 94% precision from synchronised activity | [DeBot](https://www.cs.unm.edu/~chavoshi/debot/SocInfo.pdf) |
| Stylometry, text reuse | No: needs the content | 20% top-1 among 100,000 authors; fails against deliberate obfuscation | [Narayanan et al. 2012](https://www.ieee-security.org/TC/SP2012/papers/4681a300.pdf) |

**The honest limit:** per-IP evidence does not survive residential proxies, and the strongest fingerprints are invisible in plain logs.

**More signal from stock nginx, with one `log_format` change:** `$msec`, `$request_time`, `$connection_requests`, and the client's `$ssl_ciphers` and `$ssl_curves` ([ssl module](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)). The last two give a rough TLS fingerprint without rebuilding. Full JA4 needs nginx 1.26 or later with a patch ([ja4-nginx-module](https://github.com/FoxIO-LLC/ja4-nginx-module)).

## 3. Bot detection in logs

**Labelled dataset** (record checked directly). [Web robot detection: server logs, Zenodo](https://zenodo.org/records/3477932), CC BY 4.0, Lagopoulos & Tsoumakas.

- One month (March 2018) of the search engine of a university library: 4,091,155 requests, 27,061 unique IPs, 3,441 user-agent strings.
- Files: the raw logs as JSON (3.2 GB), and two ready-made session tables with labels and features, `simple_features.csv` (15.9 MB) and `semantic_features.csv` (4.3 MB). The CSVs are enough to train and measure a first session classifier without parsing the raw logs.
- Limits: one site, 2018, so no AI crawlers and a real domain shift. **The last digits of each IP are masked**, so ASN, hosting and VPN lookups (signals 1 and 2) cannot be evaluated on it. How its labels were produced was not checked.

**Sessions.** Group by IP plus user agent, 30 minutes of inactivity ends a session, drop sessions under 3 requests ([Lagopoulos & Tsoumakas](https://arxiv.org/abs/1711.05098)).

**Features** most used across 34 studies ([mapping study](https://sbia.org.br/wp-content/uploads/2021/09/pdf/CBIC_2021_paper_60.pdf)): number of requests, session duration, share of empty referrers, share of 4xx responses, share of HEAD requests, robots.txt or trap-file access, bytes transferred, share of image requests and image-to-page ratio. Useful additions: standard deviation of the time between requests, share of repeated requests, sequential-request ratio, standard deviation of page depth ([Stevanovic et al. 2012](https://www.sciencedirect.com/science/article/abs/pii/S0957417412002382)).

**Models.** The most used are SVM, decision trees, naive Bayes, neural networks and random forests (mapping study); gradient boosting did best on simple features (Lagopoulos & Tsoumakas). Logs alone are weaker against human-like bots than mouse data, and accuracy settles after about 30 requests ([Iliou et al. 2021](https://doi.org/10.1145/3447815)).

**Verifying declared bots.**

- Google: reverse DNS ends in `googlebot.com`, `google.com` or `googleusercontent.com` and resolves back to the same IP, or the IP is in the [published ranges](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot).
- Bing: [verification page](https://www.bing.com/webmasters/help/verify-bingbot-2195837f), [bingbot.json](https://www.bing.com/toolbox/bingbot.json).
- OpenAI: [gptbot.json](https://openai.com/gptbot.json).
- Emerging: signed requests ([Web Bot Auth](https://developers.cloudflare.com/bots/reference/bot-verification/web-bot-auth/)); needs the `Signature-Agent` header in the log.

**Credential stuffing against brute force.** Brute force is many passwords against one account; stuffing is breached pairs tried across many accounts through proxies ([OWASP OAT-008](https://owasp.org/www-project-automated-threats-to-web-applications/assets/oats/EN/OAT-008_Credential_Stuffing)). Combined logs carry no usernames, so the two cannot be told apart with certainty without the application's own auth log.

**Open tools to learn from.** [CrowdSec](https://github.com/crowdsecurity/crowdsec) (MIT; its [HTTP scenarios](https://app.crowdsec.net/hub/author/crowdsecurity/collections/base-http-scenarios) are readable rules), [GoAccess](https://goaccess.io/) (MIT), [crawler-user-agents](https://github.com/monperrus/crawler-user-agents) and [ai.robots.txt](https://github.com/ai-robots-txt/ai.robots.txt) (MIT, user-agent lists), [OWASP Automated Threats](https://owasp.org/www-project-automated-threats-to-web-applications/) (the taxonomy; scraping now names LLM scrapers).

## 4. Free data for IP classification

| Source | Content | Terms |
| --- | --- | --- |
| [IPinfo Lite](https://ipinfo.io/developers/ipinfo-lite-database) | Country and ASN, file or API | CC BY-SA 4.0, attribution, token. No VPN flag |
| [iptoasn.com](https://iptoasn.com/) | IP to ASN, hourly file | PDDL 1.0 |
| [ipverse/asn-ip](https://github.com/ipverse/asn-ip) | Prefixes per ASN | CC0 |
| [X4BNet lists_vpn](https://github.com/X4BNet/lists_vpn) | VPN and datacentre ranges | MIT (upstream data CC BY-SA 4.0) |
| [FireHOL blocklist-ipsets](https://github.com/firehol/blocklist-ipsets) | Aggregated lists: anonymisers, proxies, abusers | Each component has its own licence |
| [Tor bulk exit list](https://check.torproject.org/torbulkexitlist) | Exit IPs | Official |
| [AWS](https://ip-ranges.amazonaws.com/ip-ranges.json), [Google Cloud](https://www.gstatic.com/ipranges/cloud.json), [iCloud Private Relay](https://mask-api.icloud.com/egress-ip-ranges.csv) | Published ranges | Public files |
| [MaxMind GeoLite](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/) | Country, city, ASN | Own licence, attribution, account. Proxy data is paid |

Licence trap: JA4 (TLS client) is BSD 3-Clause, but the rest of the JA4+ family is under a licence that forbids monetisation without an agreement.

## 5. What CAPTCHA research says

- Bots beat humans on deployed CAPTCHAs: 85 to 100% against 50 to 85% ([Searles et al., USENIX Security 2023](https://arxiv.org/abs/2307.12108)).
- reCAPTCHA v2 image challenges solved 100% of the time with off-the-shelf vision models ([Plesner et al. 2024](https://arxiv.org/abs/2409.08831)).
- reCAPTCHA v3 behavioural scoring passed 97.4% of the time by a reinforcement-learning mouse agent ([Akrout et al. 2019](https://arxiv.org/abs/1903.01003)).
- A general vision-language solver passed 60.7% of 2,600 challenges ([Halligan, USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/teoh)).
- LLM browser agents: 40% at most against 93.3% for humans in 2025 ([Open CaptchaWorld](https://arxiv.org/abs/2505.24878)); 2026 preprints report much higher rates for newer models and solver services ([Next-Gen CAPTCHAs](https://arxiv.org/html/2602.09012v1), [Broken Gates](https://arxiv.org/html/2607.18659)).

What invisible systems rely on now: an interaction score ([reCAPTCHA v3](https://developers.google.com/recaptcha/docs/v3)), proof-of-work plus browser probing ([Turnstile](https://developers.cloudflare.com/turnstile/), [Anubis](https://github.com/TecharoHQ/anubis)), and device attestation ([Private Access Tokens](https://blog.cloudflare.com/eliminating-captchas-on-iphones-and-macs-using-new-standard/)).

**Takeaway.** A passed challenge is not proof of a human. Score behaviour and network evidence, and keep a challenge for the uncertain band only: blocking clients without JavaScript harms screen-reader users.

## 6. Provenance signals for a source

| Signal | How | Limits |
| --- | --- | --- |
| Domain age | RDAP: `https://rdap.org/domain/<name>` ([docs](https://about.rdap.org/)) | 10 requests per 10 s. RDAP replaced WHOIS for generic domains in January 2025 |
| Certificate history | `https://crt.sh/?q=<domain>&output=json`; fallback [Cert Spotter](https://sslmate.com/help/reference/ct_search_api_v1) | crt.sh is flaky: cache |
| First archive capture | Wayback [availability](https://archive.org/help/wayback_api.php) and [CDX](https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md) APIs | Heavy use gets a temporary ban |
| Hosting overlap | DNS over HTTPS ([Google](https://developers.google.com/speed/public-dns/docs/doh/json)), then IP to ASN | Shared hosting makes "same IP" a weak link |
| Shared analytics and ad identifiers | Regex for `UA-`, `G-`, `GTM-`, `ca-pub-` in the HTML; `/ads.txt`; history through [wayback-google-analytics](https://github.com/bellingcat/wayback-google-analytics) (MIT) | A strong link between sites when present |
| Content cloning | [trafilatura](https://github.com/adbar/trafilatura) (Apache 2.0) for the text, then MinHash ([datasketch](https://ekzhu.com/datasketch/lsh.html), MIT) or SimHash | CPU only; verify candidates with exact similarity |
| Popularity | [Tranco top 1M](https://tranco-list.eu/) | Mixed licences in its components |
| Reliability lists | [Iffy Index](https://iffy.news/index/) (CC BY 4.0); [domain quality ratings](https://github.com/hauselin/domain-quality-ratings) | News domains only; the second has no stated licence |
| Threat lists | [URLhaus](https://urlhaus.abuse.ch/api/) (free key); [Safe Browsing](https://developers.google.com/safe-browsing/v4/usage-limits) | Safe Browsing is non-commercial and requires hedged wording |

**AI-generated text: low weight.** OpenAI withdrew its own classifier (26% detection at 9% false positives, [source](https://openai.com/index/new-ai-classifier-for-indicating-ai-written-text/)). Detectors misclassify non-native English writing as AI ([Liang et al.](https://arxiv.org/abs/2304.02819)). [Binoculars](https://arxiv.org/abs/2401.12070) reports strong results but runs two language models, heavy for this server.

## 7. Not verified

- Rate limits of crt.sh, the Wayback availability API and the DNS-over-HTTPS endpoints are not documented on the pages read.
- Seen only as an abstract or through a secondary source: Stevanovic 2012, the OWASP handbook symptoms for credential stuffing, the accuracy figure of the round-trip method.
- No licence file found for FireHOL blocklist-ipsets and for the coordination-detection code of Pacheco et al.
- Not checked: Spamhaus, PhishTank and OpenPhish terms, NewsGuard, Media Bias/Fact Check, Common Crawl graph sizes.
- Stated without a source: tools that impersonate a browser's TLS handshake defeat JA3 and JA4.
- A context figure for the pitch, vendor data: 53% of 2025 web traffic automated, 40% bad bots ([Imperva 2026 report](https://www.imperva.com/blog/bad-bot-report-2026-bots-agentic-age/)).
