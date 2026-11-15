/* Everything the method page reads from the server, and what is derived from it once. */

import { useMemo } from 'react'
import { fetchMethod } from '../api/method'
import type { Method } from '../api/methodSchema'
import type { Request } from '../api/useRequest'
import { useRequest } from '../api/useRequest'
import { fetchConfig, fetchMetrics } from '../api/workspace'
import type { Metrics, PublicConfig } from '../api/workspaceSchema'
import type { Facts } from './pipeline/facts'
import type { ProbeFiles } from './probeFiles'
import { readProbeFiles } from './probeFiles'
import type { LevelStarts } from './probes/setting'
import type { Reports } from './reports'
import { NO_REPORTS, readReports } from './reports'

export interface MethodData {
  method: Request<Method>
  metrics: Request<Metrics>
  config: Request<PublicConfig>
  /** The method once it is read; null while it loads or when the server does not publish it. */
  data: Method | null
  reports: Reports
  files: ProbeFiles
  /** Where the two levels start on the score scale. */
  starts: LevelStarts | null
  facts: Facts
  /** Keys of the probes that exist: measured by the report, or served. */
  probeKeys: ReadonlySet<string>
}

export function useMethodData(): MethodData {
  const method = useRequest(fetchMethod)
  const metrics = useRequest(fetchMetrics)
  const config = useRequest(fetchConfig)
  const data = method.status === 'ready' ? method.data : null
  const measured = metrics.status === 'ready' ? metrics.data : null
  const settings = config.status === 'ready' ? config.data : null

  const reports = useMemo(() => (measured ? readReports(measured) : NO_REPORTS), [measured])
  const files = useMemo(() => readProbeFiles(data?.probe_files ?? {}), [data])
  const starts = useMemo(() => (settings ? { possible: settings.possible_score, probable: settings.probable_score } : null), [settings])
  const facts = useMemo<Facts>(() => ({ method: data, metrics: measured, reports, starts }), [data, measured, reports, starts])
  const probeKeys = useMemo(
    () => new Set([...Object.keys(reports.probes?.targets ?? {}), ...(measured?.probes.map((probe) => probe.key) ?? [])]),
    [reports, measured],
  )
  return { method, metrics, config, data, reports, files, starts, facts, probeKeys }
}
