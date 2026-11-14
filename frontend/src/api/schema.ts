/* Shapes of what the API returns, validated where they enter the app. */

import { z } from 'zod'

export const bufferSpecSchema = z.object({
  dtype: z.enum(['float32', 'float64', 'uint8', 'uint16', 'uint32']),
  offset: z.number().int().nonnegative(),
  length: z.number().int().nonnegative(),
})

export const manifestSchema = z.object({
  build: z.string(),
  built_at: z.string(),
  n: z.number().int().positive(),
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

const rateSchema = z.number().nullable()

/** One measured rate of a detector, with the data it was measured on. */
export const measureSchema = z.object({
  name: z.string(),
  kind: z.string(),
  set: z.string(),
  n: z.number().int(),
  value: z.number(),
  low: rateSchema,
  high: rateSchema,
})

/** The evaluation report of a detector, as its evaluation code wrote it. */
export const detectorMetricsSchema = z.object({
  detector: z.string(),
  title: z.string(),
  report: z.string(),
  date: z.string(),
  unit: z.string(),
  decides: z.string(),
  operating_point: z.record(z.string(), z.unknown()),
  results: z.array(measureSchema),
  precision_at_base_rates: z.array(
    z.object({ prevalence: z.number(), precision: z.number(), low: rateSchema, high: rateSchema }),
  ),
  false_positive_modes: z.array(z.object({ mode: z.string(), example: z.string(), response: z.string() })),
  untested: z.array(z.string()),
})

export const metricsResponseSchema = z.object({ detectors: z.array(detectorMetricsSchema) })

const confidenceSchema = z.enum(['probable', 'possible'])

const swarmSummaryShape = {
  id: z.number().int(),
  name: z.string(),
  confidence: confidenceSchema,
  n_actors: z.number().int(),
  n_events: z.number().int(),
  first_at: z.number(),
  last_at: z.number(),
}

export const actorVerdictSchema = z.object({
  swarm: z.number().int(),
  confidence: confidenceSchema,
  n_events: z.number().int(),
  n_partners: z.number().int(),
})

export const swarmLayerSchema = z.object({
  detector: z.string(),
  window_seconds: z.number(),
  min_events: z.number(),
  swarms: z.array(z.object(swarmSummaryShape)),
  actors: z.record(z.string(), actorVerdictSchema),
  reliability: detectorMetricsSchema,
})

export const swarmSchema = z.object({
  ...swarmSummaryShape,
  actors: z.array(z.object({ actor_id: z.string(), n_events: z.number().int(), n_partners: z.number().int() })),
  events: z.array(
    z.object({ at: z.number(), text: z.string(), actor_ids: z.array(z.string()), spread_seconds: z.number() }),
  ),
  weeks: z.array(z.object({ start: z.number(), events: z.number().int() })),
})

export type Measure = z.infer<typeof measureSchema>
export type DetectorMetrics = z.infer<typeof detectorMetricsSchema>
export type Confidence = z.infer<typeof confidenceSchema>
export type ActorVerdict = z.infer<typeof actorVerdictSchema>
export type SwarmLayer = z.infer<typeof swarmLayerSchema>
export type Swarm = z.infer<typeof swarmSchema>
export type Manifest = z.infer<typeof manifestSchema>
export type Analysis = z.infer<typeof analysisSchema>
export type BufferSpec = z.infer<typeof bufferSpecSchema>
export type Item = z.infer<typeof itemSchema>
export type Health = z.infer<typeof healthSchema>
