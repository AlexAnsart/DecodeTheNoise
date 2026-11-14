/* The API in words: one definition for the prompt a coding agent receives, the curl command
   and the reference on the method page. It follows backend/ingest/schema.py. */

export interface Endpoint {
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  path: string
  what: string
}

export interface FieldDoc {
  name: string
  required: boolean
  type: string
  meaning: string
}

export const API_BASE_PATH = '/api/v1'
export const KEY_VARIABLE = 'NOISEMAP_API_KEY'

export const ENDPOINTS: Endpoint[] = [
  { method: 'POST', path: '/items', what: 'Store one post. The answer comes at once, with its scores and its context. Options: ?store=false reads the post without keeping it, ?vector=true adds its embedding, ?neighbours=0 to 20.' },
  { method: 'POST', path: '/items/batch', what: 'Store many posts, {"items": [...]}. They are embedded in the background.' },
  { method: 'GET', path: '/items/{id}', what: 'The answer for one post, once it has been placed.' },
  { method: 'GET', path: '/workspace', what: 'Counts, limits, usage and settings of the workspace.' },
  { method: 'PATCH', path: '/workspace/settings', what: 'Change which flagged posts go to the LLM review, and how often topics refresh.' },
  { method: 'DELETE', path: '/workspace/items', what: 'Empty the workspace.' },
  { method: 'POST', path: '/workspace/key', what: 'A new key. The old one stops working.' },
  { method: 'GET', path: '/events', what: 'A server-sent event stream: the state of the workspace each time it changes.' },
]

export const ITEM_FIELDS: FieldDoc[] = [
  { name: 'id', required: true, type: 'string', meaning: 'Your identifier of the post. Sending the same id again updates the post.' },
  { name: 'text', required: true, type: 'string', meaning: 'The text of the post.' },
  { name: 'created_at', required: false, type: 'ISO 8601 with offset', meaning: 'When the post was published, for example 2026-11-14T09:31:07Z. Left out: the post is undated.' },
  { name: 'actor_id', required: false, type: 'string', meaning: 'A stable identifier of the author. Without it there is no context by author.' },
  { name: 'actor_name', required: false, type: 'string', meaning: 'A display name for the author.' },
  { name: 'kind', required: false, type: 'original | reply | repost | quote', meaning: 'What the post is.' },
  { name: 'parent_id', required: false, type: 'string', meaning: 'The post this one answers, reposts or quotes.' },
  { name: 'parent_actor_id', required: false, type: 'string', meaning: 'Who wrote that post.' },
  { name: 'urls', required: false, type: 'string[]', meaning: 'The links in the post.' },
  { name: 'lang', required: false, type: 'string', meaning: 'Language code of the text, for example en.' },
  { name: 'source', required: false, type: 'string', meaning: 'Where the post comes from: a platform, a feed.' },
  { name: 'meta', required: false, type: 'object', meaning: 'Up to 16 values of your own (strings, numbers, booleans).' },
]

/** The parts of an answer, with what each one says. No value here is a measurement. */
export const ANSWER_SHAPE = `{
  "id": "post-1842",
  "stored": true,
  "outcome": "placed",               // or "queued" (batch), "not enough evidence" (too short)
  "reason": null,                    // why the post is not placed
  "index": 341,                      // its point on the map
  "item": {                          // read from the post alone
    "lang": "en",
    "probes": [                      // the probes that flagged it, strongest first
      { "key": "…", "label": "…", "score": …, "level": "possible" | "probable",
        "reliability": { "precision": …, "false_positive_rate": …, "read": … },
        "report": "…" }
    ],
    "scores": { "<probe>": … },      // every probe: 0.5 starts "possible", 0.8 "probable"
    "review": { "status": "none" | "queued" | "done" | "skipped" | "failed", "findings": [] }
  },
  "context": {                       // read from the rest of your workspace
    "position": [x, y, z],
    "zone": { "id": …, "name": "…", "share": … },
    "neighbours": [ { "id": "…", "actor_id": "…", "similarity": …, "word_overlap": …, "excerpt": "…" } ],
    "same_statement": { "min_similarity": …, "items": …, "actors": …, "first": "…", "last": "…" },
    "actor": { "id": "…", "items": …, "similar_actors": [ { "id": "…", "similarity": …, "items": … } ] }
  },
  "vector": null,                    // the embedding of the post, with ?vector=true
  "workspace": { "items": …, "points": …, "pending": …, "limit": …, "next_refresh_at": … }
}`

const SAMPLE_POST = {
  id: 'post-1',
  text: 'Fuel prices are up again and nobody in charge seems to care.',
  created_at: '2026-11-14T09:31:07Z',
  actor_id: 'user-42',
  kind: 'original',
}

/** One post sent from a terminal. */
export function curlExample(origin: string, key: string): string {
  return [
    `curl -X POST ${origin}${API_BASE_PATH}/items \\`,
    `  -H "Authorization: Bearer ${key}" \\`,
    '  -H "Content-Type: application/json" \\',
    `  -d '${JSON.stringify(SAMPLE_POST)}'`,
  ].join('\n')
}

/** What a coding agent needs to wire an application to the API, in one message. */
export function agentPrompt(origin: string, key: string, batchItems: number): string {
  const base = `${origin}${API_BASE_PATH}`
  const optional = ITEM_FIELDS.filter((field) => !field.required)
  return `Connect this project to NoiseMap.

NoiseMap places every post on a map of meaning and reads it with measured probes. Send it the posts this application handles; for each one it returns scores and what surrounds it.

Setup
- Add ${KEY_VARIABLE}=${key} to .env (git-ignored) and read it from the environment. Never write the key in code, in a log or in a commit.
- Base URL: ${base}. Every request carries the header "Authorization: Bearer $${KEY_VARIABLE}".

Sending posts
- When a post is published or received: POST ${base}/items with one JSON object. The answer comes at once.
- For the history: POST ${base}/items/batch with {"items": [...]}, up to ${batchItems.toLocaleString('en-US')} per call. A batch is processed in the background; GET ${base}/items/{id} gives the answer for one post later.
- Sending the same id again updates the post, so a retry is safe.

Fields of a post. Only "id" and "text" are required; an unknown field is refused with 422.
- id (string): this application's identifier of the post.
- text (string): the text of the post.
${optional.map((field) => `- ${field.name} (${field.type}): ${field.meaning}`).join('\n')}

What comes back
- outcome: "placed", "queued" (batch) or "not enough evidence" (text too short), with "reason".
- item.probes: the probes that flagged the post, each with its level ("possible" or "probable") and the measured reliability of that level. item.scores: one score per probe, where 0.5 starts "possible" and 0.8 "probable". item.review: the LLM review, when one ran.
- context.zone: the topic the post falls in. context.neighbours: the nearest posts by meaning, with "similarity" and "word_overlap". context.same_statement: how many other posts and authors say the same thing. context.actor: the author's activity and the authors who write alike.
- Options of POST ${base}/items: ?store=false reads a post without keeping it; ?vector=true adds its embedding to the answer.

Rules
- On 429, wait for the seconds given by the Retry-After header, then try again. On 401 the key is wrong: stop and say so.
- Map this application's own post model to the fields above. Leave out a field the application does not have: do not invent a value, and do not send the current time as created_at.
- A probe flags, it does not convict: show a level with its reliability, never a bare score.`
}
