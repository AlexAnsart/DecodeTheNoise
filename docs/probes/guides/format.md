# Guide: format

Version: v2. Read `common.md` first.

This guide has eight labels about the form of the post. Seven take `yes`, `no` or `unclear`. One, `lang`, takes a language code. A post can get several `yes`, or none.

Rule 3 of `common.md` (own voice) does not apply to this guide: several labels are about reporting or quoting.

Evidence for every label of this guide: none.

## `news_headline`

**Question.** Is the whole post a press headline, with no comment from the author?

**YES when all are true:**

1. The post states an event, an announcement or a finding in the impersonal third person, the way a news headline or the first sentence of a news article does.
2. It has no first person, no opinion of the author, and does not address the reader.
3. Nothing else is added, apart from a link, a source name ("BBC", "| Reuters"), hashtags or emojis.

**NO when:**

- the author adds a comment, however short ("Unbelievable.", "About time");
- the post is made of structured data fields (that is `automated_alert`).

**Examples.**

- YES: "Parliament approves new budget after 12-hour debate https://…"
- YES: "Reuters: Oil prices fall as talks resume"
- NO: "Parliament approves the new budget. What a joke"
- NO: "I think parliament will approve the budget tonight"

## `automated_alert`

**Question.** Is the post a data alert produced by a machine?

**YES when both are true:**

1. The post follows a fixed pattern of data fields: values, units, codes, times, places.
2. It is one of: a weather warning or reading, an earthquake notice, a traffic or transit status, a stock or crypto price tick, a sports score update, a flight or ship position, an air-quality reading, a system status.

**NO when:**

- a person describes the same thing in free prose ("it's pouring here in Leeds");
- the post is a news headline about the event.

**Examples.**

- YES: "M 4.2 - 10 km SE of Ridgecrest, CA. 2026-06-11 20:41 UTC. Depth 8 km"
- YES: "BTC/USD 64,210.5 ▲ 1.2% (24h) | Vol 31.2B"
- NO: "Felt a small earthquake just now, anyone else?"

## `templated_post`

**Question.** Is the post the fixed text of an app or a sharing button, where only a title or a number changes?

**YES when both are true:**

1. The post is boilerplate written by an app or a sharing function, not free prose.
2. It shows such a template: "I just published …", "New video: …", "I liked a @YouTube video", "I'm listening to … on Spotify", "Now playing: …", "Just completed a 5 km run with …", "I'm at … (via …)", "My week on X: 5 mentions, 12 likes", a daily game score grid, an automatic "Thanks for the follow".

**NO when:**

- the author writes freely about a video, a song or a run;
- the post is a data alert (that is `automated_alert`) or a press headline (that is `news_headline`).

**Examples.**

- YES: "I liked a @YouTube video: 10 Minute Morning Yoga https://…"
- YES: "Just completed a 5.2 km run with RunApp. Check it out! https://…"
- NO: "This yoga video really helped my back, recommend it"

## `quote_post`

**Question.** Is the whole post a saying, with no comment from the author?

**YES when all are true:**

1. The post consists of a quotation: an aphorism, a proverb, a verse of scripture, a line from a book, a poem or a song, a motivational saying.
2. It is marked as a quotation: quotation marks, an attribution ("— Name", "Name:"), or a chapter and verse.
3. Nothing else is added, apart from hashtags or emojis.

**NO when:**

- the quoted words are a statement about current events ("'We will not raise taxes' — the PM");
- the author adds a comment.

**Examples.**

- YES: "\"The only way out is through.\" — Robert Frost"
- YES: "Be still, and know that I am God. Psalm 46:10 🙏"
- NO: "\"The only way out is through.\" Needed this today after the week I've had"

## `reported_speech`

**Question.** Does the post report or quote what someone else said or wrote?

**YES when:**

1. The post reports or quotes the words or claims of someone other than the author: quotation marks with an attribution, "X said", "X says", "X claims", "X announced", "according to X", "X: …".

**NO when:**

- the quotation marks only surround one word or a title ("the so-called \"reform\"");
- the post only states what the author thinks.

**Examples.**

- YES: "The minister said taxes will not rise this year"
- YES: "\"The only way out is through.\" — Robert Frost"
- NO: "Taxes will not rise this year, mark my words"

## `irony`

**Question.** Does the post obviously mean the opposite of what it says?

**YES when:**

1. The reversal is obvious from the text itself: a marker ("/s", "yeah right", "sure, because …"), mock praise of a failure ("great job, really"), "what could possibly go wrong".

**NO when:**

- the post is humour without reversal: a joke, a pun, a meme caption;
- you are not sure. Take the post literally.

**Examples.**

- YES: "Oh great, another tax. Just what we needed"
- YES: "Sure, because that worked so well last time /s"
- NO: "Why did the chicken cross the road? To get to the other side"

## `not_enough_text`

**Question.** Does the post say too little to be judged on its own?

**YES when either is true:**

1. The post has fewer than four words once URLs and `@name` mentions are removed. A hashtag counts as one word.
2. The post only points at something that is not shown (a picture, a link, the post it answers) and says nothing by itself: "This.", "Look at this 👇", "Agreed 100%", "Same here lol", "Thread 🧵".

**NO when:**

- the post states something by itself, even briefly ("Taxes are too high.", "Great match tonight").

**Examples.**

- YES: "@dave lol same"
- YES: "This 👆👆 https://…"
- NO: "Great match tonight, what a goal"

## `lang`

**Question.** What is the main language of the words of the post?

**Answer with one code:**

| Code | Language |
| --- | --- |
| `en` | English |
| `de` | German |
| `es` | Spanish |
| `fr` | French |
| `pt` | Portuguese |
| `it` | Italian |
| `nl` | Dutch |
| `tr` | Turkish |
| `ar` | Arabic |
| `ja` | Japanese |
| `ru` | Russian |
| `hi` | Hindi |
| `id` | Indonesian or Malay |
| `other` | Any other language |
| `none` | The post has no words in any language |

**Rules.**

1. Names, `@name` mentions, hashtags, URLs, numbers and emojis are not words.
2. If several languages are present, answer the one with the most words. On a tie, answer the language of the first sentence.
3. Answer `none` when nothing is left after rule 1.

**Examples.**

- "Das ist doch völlig absurd, oder?" → `de`
- "Bonne nuit everyone, à demain pour la suite" → `fr`
- "@dave 😂😂 https://…" → `none`
