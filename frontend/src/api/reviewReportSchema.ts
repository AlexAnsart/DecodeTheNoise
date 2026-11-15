/* The evaluation of the LLM review (`reports/review/metrics.json`, served by `GET /api/metrics`).
   Read field by field: the file is still growing, so a field that is absent, null or of
   another shape reads as absent, and the page says "not measured" in its place. */

import { z } from 'zod'

const count = z.number().nullable().optional().catch(undefined)
const text = z.string().nullable().optional().catch(undefined)
/** A measured rate with its 95% interval. */
const rate = z.object({ value: z.number(), low: z.number(), high: z.number() }).nullable().optional().catch(undefined)

/** The technique screen against the annotation, for one technique. */
const reviewLabelSchema = z.object({
  /** Posts compared, posts annotated yes, posts the review named the technique on. */
  n: count,
  positives: count,
  marked: count,
  tp: count,
  fp: count,
  fn: count,
  precision: rate,
  recall: rate,
  fpr: rate,
  f1: count,
  /** Cohen's kappa of the review with the annotation, then of two annotators together. */
  kappa: count,
  reference_kappa: count,
  /** False when two annotators agree too little on the technique for a rate to mean much. */
  measurable: z.boolean().nullable().optional().catch(undefined),
})

/** Every (post, technique) pair of the measurable techniques, counted together. */
const pooledSchema = z.object({
  tp: count,
  fp: count,
  fn: count,
  tn: count,
  precision: rate,
  recall: rate,
  fpr: rate,
  /** Share of the pairs answered like the annotation: by the review, and by naming nothing. */
  agreement: rate,
  agreement_without_review: rate,
})

/** The same posts asked twice, cache bypassed. */
const runsSchema = z.object({
  asked: count,
  /** Posts with a readable answer in both runs. */
  posts: count,
  same_posts: rate,
  decisions: count,
  same_decisions: rate,
})

/** One probe, then the review on what it flagged. */
const cascadeProbeSchema = z.object({
  flagged: count,
  flagged_yes: count,
  after_probe: rate,
  read: count,
  read_yes: count,
  kept: count,
  kept_yes: count,
  after_review: rate,
  /** Measured by score band only: the test posts the probe flags, and the share of its true
   *  positives the review keeps. */
  flagged_in_split: count,
  true_positives_kept: rate,
  /** "head" when only its highest scores were read enough to be measured. */
  scope: text,
})

const cascadeSchema = z.object({
  /** "bands" when each band of scores counts for the test posts it holds. */
  design: text,
  pack_run: text,
  posts: count,
  posts_flagged: count,
  posts_read: count,
  probes: z.record(z.string(), cascadeProbeSchema.catch({})).catch({}),
})

export const reviewReportSchema = z.object({
  model: text,
  prompt_version: text,
  temperature: count,
  /** What the review was compared with, in the words of the evaluation. */
  reference: text,
  split: text,
  asked: count,
  accounts: count,
  /** Posts with an answer that could be read, and answers that could not. */
  posts: count,
  failed: count,
  /** Quotes that were not found in the post they were given for. */
  rejected_quotes: count,
  labels: z.record(z.string(), reviewLabelSchema.catch({})).catch({}),
  pooled: pooledSchema.nullable().optional().catch(undefined),
  runs_agreement: runsSchema.nullable().optional().catch(undefined),
  cascade: cascadeSchema.nullable().optional().catch(undefined),
  /** The same cascade on every test post read by score band: more posts, narrower intervals. */
  cascade_bands: cascadeSchema.nullable().optional().catch(undefined),
})

export type Rate = NonNullable<z.infer<typeof rate>>
export type ReviewLabel = z.infer<typeof reviewLabelSchema>
export type ReviewPooled = z.infer<typeof pooledSchema>
export type ReviewRuns = z.infer<typeof runsSchema>
export type ReviewCascade = z.infer<typeof cascadeSchema>
export type ReviewReport = z.infer<typeof reviewReportSchema>
