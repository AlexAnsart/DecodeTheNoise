/* Shapes of what the map routes return, validated where they enter the app. */

import { z } from 'zod'
import { levelMeasureSchema, probeInfoSchema } from './workspaceSchema'

export const bufferSpecSchema = z.object({
  dtype: z.enum(['float32', 'float64', 'uint8', 'uint16', 'uint32']),
  offset: z.number().int().nonnegative(),
  length: z.number().int().nonnegative(),
})

export const manifestSchema = z.object({
  build: z.string(),
  built_at: z.string(),
  // An empty workspace has no point yet.
  n: z.number().int().nonnegative(),
  k: z.number().int().nonnegative(),
  embedding_key: z.string(),
  dims: z.number().int().positive(),
  time_min: z.number().nullable(),
  time_max: z.number().nullable(),
  columns: z.array(
    z.object({ key: z.string(), label: z.string(), names: z.array(z.string()), buffer: z.string() }),
  ),
  zones: z.array(
    z.object({
      id: z.number().int(),
      name: z.string(),
      words: z.array(z.string()),
      size: z.number().int(),
      named: z.boolean(),
    }),
  ),
  buffers: z.record(z.string(), bufferSpecSchema),
  // A workspace map grows: its version changes with every point, layout, name or review.
  live: z.boolean().default(false),
  version: z.number().int().nonnegative().default(0),
  probes: z.array(probeInfoSchema).default([]),
})

export const itemSchema = z.object({
  index: z.number().int(),
  item_id: z.string(),
  actor_id: z.string(),
  text: z.string(),
  created_at: z.number().nullable(),
  lang: z.string().nullable(),
  repost_of: z.string().nullable(),
  urls: z.array(z.string()),
  attrs: z.record(z.string(), z.union([z.string(), z.number(), z.boolean(), z.null()])),
})

export const itemsResponseSchema = z.object({ items: z.array(itemSchema) })

export const healthSchema = z.object({
  status: z.string(),
  commit: z.string(),
  build: z.string().nullable(),
  points: z.number().int(),
})

export const analysisSchema = z.object({
  outcome: z.enum(['placed', 'not enough evidence']),
  reason: z.string().nullable(),
  source: z.object({
    kind: z.enum(['text', 'url']),
    url: z.string().nullable(),
    title: z.string().nullable(),
    read_at: z.string().nullable(),
  }),
  text: z.string(),
  characters: z.number().int(),
  position3: z.tuple([z.number(), z.number(), z.number()]).nullable(),
  position2: z.tuple([z.number(), z.number()]).nullable(),
  neighbours: z.array(z.object({ index: z.number().int(), score: z.number() })),
  verdicts: z.array(z.unknown()),
})

export const probeReadingSchema = z.object({
  key: z.string(),
  label: z.string(),
  score: z.number(),
  level: z.enum(['possible', 'probable']),
  reliability: levelMeasureSchema,
  report: z.string(),
})

export const findingSchema = z.object({
  probe: z.string(),
  reading: z.enum(['supported', 'not supported', 'unclear']),
  explanation: z.string(),
  quote: z.string().nullable(),
})

export const reviewSchema = z.object({
  status: z.enum(['none', 'queued', 'done', 'skipped', 'failed']),
  reason: z.string().nullable().default(null),
  model: z.string().nullable().default(null),
  prompt_version: z.string().nullable().default(null),
  findings: z.array(findingSchema).default([]),
  measured: z.boolean().default(false),
})

export const pointReadingSchema = z.object({
  index: z.number().int(),
  probes: z.array(probeReadingSchema),
  scores: z.record(z.string(), z.number()),
  // Null on the demo dataset: only workspace items are reviewed.
  review: reviewSchema.nullable(),
})

export type Manifest = z.infer<typeof manifestSchema>
export type Analysis = z.infer<typeof analysisSchema>
export type BufferSpec = z.infer<typeof bufferSpecSchema>
export type Item = z.infer<typeof itemSchema>
export type Health = z.infer<typeof healthSchema>
export type LevelMeasure = z.infer<typeof levelMeasureSchema>
export type ProbeInfo = z.infer<typeof probeInfoSchema>
export type ProbeReading = z.infer<typeof probeReadingSchema>
export type Finding = z.infer<typeof findingSchema>
export type Review = z.infer<typeof reviewSchema>
export type PointReading = z.infer<typeof pointReadingSchema>
