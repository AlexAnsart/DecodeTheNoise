/* The facts the page states about the product, all read from the server. Pure. */

import type { Method } from '../../api/methodSchema'
import type { Metrics } from '../../api/workspaceSchema'
import type { LevelStarts } from '../probes/setting'
import type { Reports } from '../reports'

export interface Facts {
  /** Null while the server does not publish the method. */
  method: Method | null
  metrics: Metrics | null
  reports: Reports
  starts: LevelStarts | null
}

export interface ProbeCounts {
  measured: number
  shown: number
  reviewOnly: number
  dropped: number
}

/** How many probes ended in each state: from the evaluation report when it reads, from the
 *  probes the server serves otherwise. Null when neither is known. */
export function probeCounts({ reports, metrics }: Facts): ProbeCounts | null {
  const states = reports.probes ? Object.values(reports.probes.targets).map((target) => target.state ?? '') : metrics?.probes.map((probe) => probe.state)
  if (!states || states.length === 0) return null
  const count = (state: string): number => states.filter((value) => value === state).length
  return { measured: states.length, shown: count('shown'), reviewOnly: count('review-only'), dropped: count('dropped') }
}
