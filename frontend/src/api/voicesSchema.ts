/* Shapes of the "one voice, or several?" check: its answer about a selection, and its
   evaluation report. Validated where they enter the app. */

import { z } from 'zod'

const count = z.number().int().nonnegative()
/** Where 90% of the measured groups score: low end, high end. */
const range = z.tuple([z.number(), z.number()])

const pairSideSchema = z.object({ index: count, actor: z.string(), text: z.string() })

export const voicesSchema = z.object({
  outcome: z.enum(['one voice', 'separate voices', 'not enough evidence']),
  // Set only when the outcome is `one voice`: a level, never a statement of fact.
  confidence: z.enum(['possible']).nullable(),
  reason: z.string().nullable(),
  selection: z.object({ items: count, actors: count }),
  needed: z.object({ actors: count, posts_each: count }),
  read: z.object({ actors: count, posts_each: count, eligible_actors: count, draws: count }).nullable(),
  // 0: the actors are interchangeable. Higher: each actor has a voice of its own.
  score: z.number().nullable(),
  threshold: z.number().nullable(),
  authorship: z.object({ found: z.number(), chance: z.number() }).nullable(),
  reference: z.object({ independent: range, one_brief: range }).nullable(),
  reliability: z
    .object({
      false_alarms: count,
      real_groups: count,
      hard_false_alarms: count,
      hard_real_groups: count,
      caught: count,
      one_brief_groups: count,
      report: z.string(),
    })
    .nullable(),
  pairs: z.array(z.object({ similarity: z.number(), a: pairSideSchema, b: pairSideSchema })).default([]),
  caveats: z.array(z.string()).default([]),
})

const tally = z.object({ groups: count, flagged: count })

/** The `voices` entry of `GET /api/metrics`, as the evaluation wrote it. */
export const voicesReportSchema = z.object({
  evaluated: z.string().optional(),
  unit: z.string().optional(),
  sizes: z.array(
    z.object({
      actors: count,
      posts_each: count,
      draws: count,
      threshold: z.number(),
      reference: z.object({ independent: range, independent_alike: range, one_brief: range }),
      real: tally,
      real_alike: tally,
      one_brief: tally.extend({ by_mode: z.record(z.string(), tally).default({}) }),
      precision_at_base_rate: z.record(z.string(), z.object({ measured: z.number(), worst_case: z.number() })).default({}),
    }),
  ),
  limits: z.array(z.string()).default([]),
  report: z.string().optional(),
})

export type Voices = z.infer<typeof voicesSchema>
export type VoicePair = Voices['pairs'][number]
export type VoicesReport = z.infer<typeof voicesReportSchema>
export type VoicesSize = VoicesReport['sizes'][number]
