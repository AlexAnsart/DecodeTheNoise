/* Shapes of the workspace and metrics routes, validated where they enter the app. They mirror
   backend/accounts/schema.py, backend/workspace/schema.py, backend/ingest/schema.py and
   backend/probes/schema.py. */

import { z } from 'zod'

const count = z.number().int().nonnegative()

export const limitsSchema = z.object({
  items: count,
  batch_items: count,
  requests_per_minute: count,
  reviews_per_day: count,
  text_chars: count,
})

export const levelMeasureSchema = z.object({
  precision: z.number(),
  precision_low: z.number(),
  precision_high: z.number(),
  false_positive_rate: z.number().nullable(),
  recall: z.number().nullable(),
  read: count,
  flag_rate: z.number(),
})

export const probeInfoSchema = z.object({
  key: z.string(),
  label: z.string(),
  description: z.string(),
  family: z.string(),
  state: z.enum(['shown', 'review-only']),
  possible: levelMeasureSchema.nullable(),
  probable: levelMeasureSchema.nullable(),
  report: z.string(),
})

export const reviewModeSchema = z.enum(['off', 'probable', 'possible', 'score'])

export const settingsSchema = z.object({
  review_mode: reviewModeSchema,
  review_min_score: z.number(),
  refresh_every: count,
})

/** What the server is doing with the posts that wait to be embedded. */
export const ingestSchema = z.object({
  /** Posts of the batch being embedded; 0 when nothing waits. Of them, `pending` still wait. */
  batch: count,
  /** Posts of other workspaces that are embedded before this one is finished. */
  ahead: count,
  /** Posts a second the embedding model was measured at on this server; null until measured. */
  rate: z.number().nullable(),
  /** The server's estimate of the time until nothing waits; null when it has none. */
  eta_seconds: z.number().nullable(),
  /** Why embedding is not advancing, in the server's words; null when it is. */
  error: z.string().nullable(),
})

export const workspaceInfoSchema = z.object({
  id: z.string(),
  created_at: z.string(),
  version: count,
  items: count,
  points: count,
  pending: count,
  actors: count,
  zones: count,
  limits: limitsSchema,
  usage: z.object({ reviews_today: count, names_today: count }),
  refresh: z.object({
    epoch: count,
    points_covered: count,
    next_at: count.nullable(),
    running: z.boolean(),
  }),
  settings: settingsSchema,
  ingest: ingestSchema,
  probes: z.array(probeInfoSchema),
  embedding_key: z.string(),
})

export const workspaceCreatedSchema = z.object({ api_key: z.string(), workspace: workspaceInfoSchema })

export const keyRotatedSchema = z.object({ api_key: z.string() })

export const publicConfigSchema = z.object({
  limits: limitsSchema,
  llm: z.boolean(),
  possible_score: z.number(),
  probable_score: z.number(),
})

/** Posts of the demo dataset, already in the shape the ingest route takes: sent back as they are. */
export const sampleSchema = z.object({
  source: z.string(),
  items: z.array(z.looseObject({ id: z.string(), text: z.string() })),
})

export const batchAcceptedSchema = z.object({
  accepted: count,
  updated: count,
  unchanged: count,
  rejected: z.array(z.object({ id: z.string().nullable(), reason: z.string() })),
  workspace: z.object({
    items: count,
    points: count,
    pending: count,
    limit: count,
    next_refresh_at: count.nullable(),
  }),
})

export const metricsSchema = z.object({
  probes: z.array(probeInfoSchema),
  reports: z.array(z.object({ detector: z.string(), metrics: z.record(z.string(), z.unknown()) })),
})

export type Limits = z.infer<typeof limitsSchema>
export type LevelMeasure = z.infer<typeof levelMeasureSchema>
export type ProbeInfo = z.infer<typeof probeInfoSchema>
export type ReviewMode = z.infer<typeof reviewModeSchema>
export type WorkspaceSettings = z.infer<typeof settingsSchema>
export type SettingsPatch = Partial<WorkspaceSettings>
export type Ingest = z.infer<typeof ingestSchema>
export type WorkspaceInfo = z.infer<typeof workspaceInfoSchema>
export type WorkspaceCreated = z.infer<typeof workspaceCreatedSchema>
export type PublicConfig = z.infer<typeof publicConfigSchema>
export type Sample = z.infer<typeof sampleSchema>
export type SamplePost = Sample['items'][number]
export type BatchAccepted = z.infer<typeof batchAcceptedSchema>
export type Metrics = z.infer<typeof metricsSchema>
