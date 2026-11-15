/* The evaluation reports as the evaluation code writes them (`reports/<detector>/metrics.json`,
   served whole by `GET /api/metrics`). Read leniently: a report that gains a field still
   reads, and a field that is absent is shown as "not measured". */

import { z } from 'zod'

/** A measured rate with its 95% interval. */
const intervalSchema = z.object({ value: z.number(), low: z.number(), high: z.number() })

/** What the test split measured at one threshold of one probe. */
const levelReportSchema = z.object({
  threshold: z.number().optional(),
  flagged: z.number().optional(),
  flag_rate: z.number().optional(),
  read_flagged: z.number().optional(),
  positive_flagged: z.number().optional(),
  precision: intervalSchema.nullable().optional(),
  recall: intervalSchema.nullable().optional(),
  fpr: intervalSchema.nullable().optional(),
  prevalence: intervalSchema.nullable().optional(),
  /** Low and high ends of the Wilson interval of the precision read. */
  wilson: z.array(z.number()).optional(),
  /** Base rate (as text: "0.01") to the precision the level would have there. */
  precision_at_base_rate: z.record(z.string(), z.number()).optional(),
})

const targetReportSchema = z.object({
  state: z.string().optional(),
  /** `possible` and `probable`, for the levels kept. */
  levels: z.record(z.string(), levelReportSchema).optional(),
  /** Levels that met their target on calibration and fell under the bar on test. */
  withdrawn: z.record(z.string(), levelReportSchema).optional(),
  /** For a probe with no level: what its highest scores hold. */
  head: levelReportSchema.nullable().optional(),
  ranking: z
    .object({
      n: z.number().optional(),
      positives: z.number().optional(),
      average_precision: z.number().optional(),
      chance: z.number().optional(),
    })
    .optional(),
  /** Level, then language, to [yes answers, posts read]. */
  by_language: z.record(z.string(), z.record(z.string(), z.array(z.number()))).optional(),
  /** The second reader: `yes` is [confirmed, read], `no` is [overturned, read]. */
  audit: z.object({ yes: z.array(z.number()), no: z.array(z.number()) }).partial().optional(),
  /** Why a probe that passed the bar is not shown. */
  demoted: z.string().optional(),
})

export const probesReportSchema = z.object({
  run: z.string().optional(),
  model_key: z.string().optional(),
  rounds: z.array(z.string()).optional(),
  targets: z.record(z.string(), targetReportSchema),
})

const figure = z.number().nullable().optional()

/** `agreement.json`: two annotators on the same posts, label by label. */
export const agreementSchema = z.object({
  n: figure,
  /** Cohen's kappa; null when no yes was given, so that chance agreement is total. */
  kappa: figure,
  yes_a: figure,
  yes_b: figure,
  both_yes: figure,
  /** Share of the yes answers that the other reading confirms. */
  positive_agreement: figure,
})

/** `prevalence.json`: how frequent a label is in the random sample, with its interval. */
export const prevalenceSchema = z.object({ decided: figure, yes: figure, share: figure, low: figure, high: figure })

/** `train.json`, one target: what the probe was fitted on. */
export const trainingSchema = z.object({ n: figure, positives: figure, c: figure, oof_ap: figure })

/** `diagnostics.json`, one target: the average precision of other readers of the same vector. */
export const diagnosticsSchema = z.object({
  chance: figure,
  linear: figure,
  centroid: figure,
  knn: figure,
  mlp: figure,
  /** Share of the train posts used, to the average precision reached. */
  learning_curve: z.record(z.string(), z.number().nullable()).optional(),
  /** Dimensions of the vector kept, to the average precision reached. */
  dims: z.record(z.string(), z.number().nullable()).optional(),
})

/** `thresholds.json`, one target: every candidate cut read on calibration, and the two kept. */
export const calibrationSchema = z.object({
  read: figure,
  positives: figure,
  possible: figure,
  probable: figure,
  edges: z.array(levelReportSchema).optional(),
})

export type Agreement = z.infer<typeof agreementSchema>
export type Prevalence = z.infer<typeof prevalenceSchema>
export type Training = z.infer<typeof trainingSchema>
export type Diagnostics = z.infer<typeof diagnosticsSchema>
export type Calibration = z.infer<typeof calibrationSchema>
export type Interval = z.infer<typeof intervalSchema>
export type LevelReport = z.infer<typeof levelReportSchema>
export type TargetReport = z.infer<typeof targetReportSchema>
export type ProbesReport = z.infer<typeof probesReportSchema>
