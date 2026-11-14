# Probe taxonomy

The labels annotated on the X corpus, as decided on 14 Nov 2026. The code reads the same list from `pipelines/probes/taxonomy.py`; the exact wording given to annotators is in [`guides/`](guides/).

## Rules of the list

- **One label, one closed question, decided on the text alone.** No label needs to know who the author is, what the post answers, or whether a statement is true.
- **Composite notions are derived, never annotated.** "Radical right" is `political_side` crossed with a radicality criterion (`anti_pluralism`, `call_overthrow`, `call_violence`, `dehumanisation`).
- **One annotation pass per family.** Each pass has its own guide and fresh annotators, who never see another family's labels.
- **Annotating a label does not ship it.** Each label ends as *shown*, *review-only* or *dropped*, from its measured agreement and precision ([`report.md`](report.md)).

The "Use" column is what the label is for, not a result:

| Use | Meaning |
| --- | --- |
| Probe | Candidate detector on single items |
| Descriptor | Describes a group (a swarm against its zone) or stratifies a measure. Never shown as a verdict on one item |
| LLM test | Too rare or too relational for a probe. Kept to test the LLM review pass later |
| Auxiliary | Explains errors, or triggers abstention |

## 1. Calls: the post explicitly asks the reader to do something

| Label | What the annotator decides | Use |
| --- | --- | --- |
| `call_amplify` | Asks to share, repost, copy-paste, tag, push a hashtag | Probe. Feeds the `open` value of the transparency axis |
| `call_pressure` | Asks to contact, mass-report or flood a target, petitions included | Probe. The signature of brigading |
| `call_protest` | Calls to demonstrate, gather, strike, block | Probe |
| `call_boycott` | Calls to stop buying, unsubscribe, boycott | Probe |
| `call_vote` | Calls to vote for or against, to register | Probe |
| `call_join` | Calls to join a group, a channel, a movement | Probe |
| `call_overthrow` | Calls to overthrow those in power, to insurrection, to revolution | Probe, rare |
| `call_violence` | Calls to hurt, kill or destroy | Probe, rare |

## 2. Hostility

"Aggressiveness" alone cannot be annotated consistently, so it is split into what can be seen.

| Label | What the annotator decides | Use |
| --- | --- | --- |
| `attack_addressee` | Insults or demeans the person the post speaks to | Probe. Pile-on harassment |
| `attack_person` | Insults or demeans a named third party | Probe |
| `attack_identity_group` | Demeans a group defined by origin, religion, nationality, gender, orientation, disability | Probe |
| `attack_political_group` | Demeans a camp, a party, a profession, an institution | Probe |
| `dehumanisation` | Equates people with animals, a disease, objects | Probe, rare |
| `threat` | The author announces they will cause harm | Probe, rare |
| `violence_endorsement` | Wishes, celebrates or justifies violence or a death, without calling for it | Probe, rare |
| `doxxing` | Publishes private information about a person | LLM test, rare |
| `profanity` | Contains vulgar words | Descriptor |

## 3. Rhetorical techniques

Aligned with the SemEval-2020 Task 11 taxonomy, to stay comparable. Annotated in two passes: `rhetoric` (the first seven) and `fallacies` (the rest).

| Label | What the annotator decides | Use |
| --- | --- | --- |
| `loaded_language` | A charged word that can be removed without losing the fact | Probe. Rate per group |
| `exaggeration` | Overstates or minimises beyond what the post supports | Probe |
| `fear_appeal` | Pushes a conclusion with a threat, not with evidence | Probe |
| `doubt` | Questions someone's credibility without giving grounds | Probe |
| `identity_appeal` | Leans on national or group pride | Probe |
| `us_vs_them` | Sets a virtuous "us" against a guilty "them" | Probe |
| `slogan` | A short, chantable formula; a watchword | Probe |
| `bandwagon` | "Everybody knows it or does it" used as the argument | LLM test |
| `authority_appeal` | An authority is used as the proof | LLM test |
| `unnamed_authority` | That authority is not named ("experts", "a study") | LLM test |
| `whataboutism` | Answers a reproach with a reverse reproach | LLM test |
| `straw_man` | Attacks a distorted version of the opposing position | LLM test |
| `false_dilemma` | Leaves only two options | LLM test |
| `causal_oversimplification` | One cause for a complex fact | LLM test |
| `thought_terminating_cliche` | A formula that closes the discussion | LLM test |
| `nazi_comparison` | Discredits by comparison with Nazism or the like | LLM test |

`unnamed_authority` is the form of "fabricated authority" that a text shows: whether the authority exists cannot be read from the post.

## 4. Solicitation and scams

| Label | What the annotator decides | Use |
| --- | --- | --- |
| `commercial_promo` | Promotes a product, a service, an event or a channel | Probe |
| `money_request` | Asks to send money: donation, fundraiser, tip | Probe |
| `gain_promise` | Promises a gain: crypto, trading, "earn X a day" | Probe |
| `engagement_bait` | Like, follow or repost in exchange for a reward or a contest entry | Probe |
| `off_platform_redirect` | Sends the reader to DMs, WhatsApp, Telegram, "link in bio" | Probe |
| `adult_promo` | Promotes sexual content or services | Probe |
| `testimonial` | A first-person account that recommends something | Probe. Commercial astroturfing |

## 5. Format and origin of the text

| Label | What the annotator decides | Use |
| --- | --- | --- |
| `news_headline` | A press headline, with no comment from the author | Probe. Feeds the `declared` value |
| `automated_alert` | An alert made of structured data: weather, earthquake, price, score | Probe. Feeds `declared` |
| `templated_post` | The template of a publishing tool | Probe. Feeds `declared` |
| `quote_post` | An attributed quotation or aphorism, with no comment | Probe |
| `reported_speech` | The post reports or quotes someone else's words | Auxiliary: error analysis |
| `irony` | Manifest irony or sarcasm | Auxiliary: error analysis |
| `lang` | Main language | Language probe |
| `not_enough_text` | Too short, or undecidable without context | Abstention |

## 6. Subject and orientation

| Label | What the annotator decides | Use |
| --- | --- | --- |
| `political` | Is about political life or a public policy | Descriptor. Controls topic confound |
| `theme` | One main theme in a fixed list of fourteen | Descriptor |
| `political_side` | Left, right or none | Descriptor |
| `anti_pluralism` | Denies the opponent the right to exist, speak or govern | Descriptor. Radicality criterion |
| `institution_distrust` | States that an institution lies or is rigged as a whole | Probe |
| `conspiracy_narrative` | Explains a fact by the secret plan of a powerful group | Probe |
| `endorsement` | Supports or praises a named person, party or brand | Probe. Simulated support |

Political orientation is shown at group level only. On a single item it would be a verdict on an opinion, which `detection-approach.md` §1 rules out.

## 7. Claims and sources

| Label | What the annotator decides | Use |
| --- | --- | --- |
| `checkable_claim` | Contains a factual statement that can be checked | Probe. Useful to fact-checking |
| `unsourced_statistic` | Gives a figure with no source | Probe |
| `hearsay` | "People say", "I heard that" | LLM test |
| `urgency_framing` | "BREAKING", "before it gets deleted", "they don't want you to see this" | Probe |

## 8. Dominant emotion

| Label | What the annotator decides | Use |
| --- | --- | --- |
| `anger` | Anger or indignation is expressed | Descriptor |
| `fear` | Fear or alarm is expressed | Descriptor |
| `contempt` | Contempt or mockery | Descriptor |
| `enthusiasm` | Enthusiasm or admiration | Descriptor |

## Not annotated

| Notion | Why |
| --- | --- |
| Bot | A property of an actor, invisible in one text |
| True or false | No label requires knowing whether a statement is accurate |
| Intent, sincerity, "propaganda" as a whole | `detection-approach.md` §1 |
| Alignment with a state | An opinion. The distinctive words of a swarm already show it |
| Repetition (SemEval) | Defined inside a long article, not inside a post |
