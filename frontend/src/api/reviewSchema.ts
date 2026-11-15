/* Shapes of the LLM review, of one item and of a selection, validated where they enter the app.
   They mirror backend/review/schema.py. */

import { z } from 'zod'

const count = z.number().int().nonnegative()
const optional = z.string().nullable().default(null)

export const reviewStatusSchema = z.enum(['none', 'queued', 'done', 'skipped', 'failed'])

/** How the review agreed with the annotation on held-out posts, for one label. */
export const reviewMeasureSchema = z.object({
  precision: z.number(),
  precision_low: z.number(),
  precision_high: z.number(),
  recall: z.number().nullable(),
  // Posts of the evaluation the review marked with this label.
  read: count,
  report: z.string(),
})

/** What the review says about one probe that flagged the item. */
export const findingSchema = z.object({
  probe: z.string(),
  label: z.string().default(''),
  reading: z.enum(['supported', 'not supported', 'unclear']),
  explanation: z.string(),
  // A span copied from the text of the item, or null when nothing in it backs the reading.
  quote: z.string().nullable(),
  reliability: reviewMeasureSchema.nullable().default(null),
})

/** A manipulation technique the review found in the text: named, explained, quoted. */
export const techniqueSchema = z.object({
  key: z.string(),
  name: z.string(),
  explanation: z.string(),
  quote: z.string(),
  reliability: reviewMeasureSchema.nullable().default(null),
})

export const reviewSchema = z.object({
  status: reviewStatusSchema,
  // Why the review was skipped or failed.
  reason: optional,
  model: optional,
  prompt_version: optional,
  findings: z.array(findingSchema).default([]),
  techniques: z.array(techniqueSchema).default([]),
  // Whose voice the text is in: the author's own, words reported or quoted, irony.
  voice: z.enum(['own', 'reported', 'ironic', 'unclear']).nullable().default(null),
  // What the text asks its reader to do, and whom it is aimed at: spans of the text.
  asks: optional,
  target: optional,
  measured: z.boolean().default(false),
  // The technique screen over every measurable technique taken together, once it is measured.
  overall: reviewMeasureSchema.nullable().default(null),
})

/** How often a probe flags the items of a selection, against the rest of the map. Counted by
 *  the probes alone: no LLM is involved. */
export const probeRateSchema = z.object({
  key: z.string(),
  label: z.string(),
  flagged: count,
  rate: z.number(),
  elsewhere: z.number(),
  // rate / elsewhere; null when the probe flags nothing elsewhere.
  lift: z.number().nullable(),
})

export const techniqueInGroupSchema = z.object({
  key: z.string(),
  name: z.string(),
  explanation: z.string(),
  // Posts of the selection that show it: the point of the map, and the span of its text.
  examples: z.array(z.object({ index: count, quote: z.string() })).default([]),
})

/** The review of a group of items: what the probes measure on it, then what the LLM reads in
 *  a sample of its posts. */
export const selectionReviewSchema = z.object({
  status: reviewStatusSchema,
  reason: optional,
  posts: count,
  actors: count,
  rates: z.array(probeRateSchema).default([]),
  // The points whose text the LLM read: a sample when the selection is large.
  read: z.array(count).default([]),
  statement: optional,
  techniques: z.array(techniqueInGroupSchema).default([]),
  asks: optional,
  targets: z.array(z.string()).default([]),
  model: optional,
  prompt_version: optional,
  measured: z.boolean().default(false),
})

export type ReviewMeasure = z.infer<typeof reviewMeasureSchema>
export type Finding = z.infer<typeof findingSchema>
export type Technique = z.infer<typeof techniqueSchema>
export type Review = z.infer<typeof reviewSchema>
export type Voice = NonNullable<Review['voice']>
export type ProbeRate = z.infer<typeof probeRateSchema>
export type TechniqueInGroup = z.infer<typeof techniqueInGroupSchema>
export type SelectionReview = z.infer<typeof selectionReviewSchema>
