/* Shapes of the method routes, validated where they enter the app. They mirror
   backend/method/schema.py. A part the server has not published is null or empty. */

import { z } from 'zod'

const count = z.number().int().nonnegative()

/** A file of the repository shown as it is: an annotation guide, the report, the journal. */
export const documentSchema = z.object({
  name: z.string(),
  title: z.string(),
  path: z.string(),
  markdown: z.string(),
})

export const labelDocSchema = z.object({
  name: z.string(),
  family: z.string(),
  /** What the label is for: probe, descriptor, llm_test, auxiliary. */
  use: z.string(),
  values: z.array(z.string()),
  question: z.string().nullable(),
  /** shown, review-only, dropped; null while the label has no evaluation. */
  state: z.string().nullable(),
})

const buildSchema = z.object({
  name: z.string(),
  points: count,
  zones: count,
  built_at: z.string(),
  embedding_key: z.string(),
  dims: count,
})

const provenanceSchema = z.object({
  dataset: z.string().nullable(),
  source_url: z.string().nullable(),
  revision: z.string().nullable(),
  files: z.array(z.string()),
  licence: z.string().nullable(),
  sample: z.record(z.string(), z.unknown()).nullable(),
})

/** What the page says in sentences of the sampling record (a free dictionary, written by the
 *  sampling step): how much was drawn, and the accounts kept on purpose when there are any.
 *  Read field by field: a field that is absent or of another shape reads as absent. */
export const drawnSampleSchema = z.object({
  items: z.number().optional().catch(undefined),
  actors: z.number().optional().catch(undefined),
  /** Hashed account ids that were asked for, not drawn; the posts they have; why, as written. */
  kept: z.object({ actors: z.array(z.string()), items: z.number(), why: z.string() }).optional().catch(undefined),
})

const reviewDocSchema = z.object({
  model: z.string().nullable(),
  prompt_version: z.string(),
  system: z.string(),
  techniques: z.array(z.object({ key: z.string(), name: z.string(), question: z.string().nullable() })),
  selection_prompt_version: z.string(),
  selection_system: z.string(),
  /** The context the review of one item reads: its nearest items, other items of its actor. */
  neighbours: count.optional(),
  actor_items: count.optional(),
  /** How a selection is read: posts sampled at most, of one actor at most, characters of each. */
  selection_posts: count.optional(),
  selection_posts_per_actor: count.optional(),
  selection_post_chars: count.optional(),
})

const labelledSummarySchema = z.object({
  /** A post read in two rounds counts once for each. */
  posts: count,
  labels: z.array(z.string()),
  splits: z.record(z.string(), count),
  rounds: z.array(z.string()),
  /** Round to its kind: `annotation`, or `second reader` for posts read again by another model. */
  round_kinds: z.record(z.string(), z.string()).default({}),
  kinds: z.record(z.string(), count).default({}),
})

export const methodSchema = z.object({
  commit: z.string(),
  repository: z.string(),
  build: buildSchema.nullable(),
  provenance: provenanceSchema.nullable(),
  labels: z.array(labelDocSchema),
  guides: z.array(documentSchema),
  documents: z.array(documentSchema),
  figures: z.array(z.string()),
  /** The other files of the probe evaluation, as written, by file name: read leniently. */
  probe_files: z.record(z.string(), z.unknown()).default({}),
  review: reviewDocSchema.nullable(),
  labelled: labelledSummarySchema.nullable(),
})

/** What one annotator answered on one post, with the span it quoted for each yes. An answer is
 *  yes, no or unclear; a label with its own values answers with one of them; `invalid` is a yes
 *  that quoted words the post does not hold, which counts as no reading. */
const readingSchema = z.object({
  reader: z.string(),
  answers: z.record(z.string(), z.string()),
  quotes: z.record(z.string(), z.string()),
})

export const labelledPostSchema = z.object({
  id: z.string(),
  text: z.string(),
  split: z.string(),
  round: z.string(),
  /** The kind of its round: `annotation` or `second reader`. */
  kind: z.string().default('annotation'),
  /** Why the post was drawn: `random`, `enrich:<label>:<source>`, `band:<label>:<n>` (several
   *  joined by `|`) or `audit:<label>`. Only the random ones are a sample of the corpus. */
  stratum: z.string().default(''),
  /** The settled answers. Empty for a second reading, which settles nothing. */
  answers: z.record(z.string(), z.string()),
  readings: z.array(readingSchema),
  scores: z.record(z.string(), z.number()),
})

export const labelledPageSchema = z.object({ total: count, posts: z.array(labelledPostSchema) })

export type Method = z.infer<typeof methodSchema>
export type MethodDocument = z.infer<typeof documentSchema>
export type LabelDoc = z.infer<typeof labelDocSchema>
export type BuildFacts = z.infer<typeof buildSchema>
export type Provenance = z.infer<typeof provenanceSchema>
export type ReviewDoc = z.infer<typeof reviewDocSchema>
export type LabelledSummary = z.infer<typeof labelledSummarySchema>
export type Reading = z.infer<typeof readingSchema>
export type LabelledPost = z.infer<typeof labelledPostSchema>
export type LabelledPage = z.infer<typeof labelledPageSchema>
