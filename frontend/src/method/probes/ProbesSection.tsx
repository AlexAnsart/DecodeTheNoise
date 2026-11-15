import { useMemo } from 'react'
import type { ReactElement } from 'react'
import type { Method } from '../../api/methodSchema'
import type { Metrics } from '../../api/workspaceSchema'
import { useMethodShared } from '../MethodContext'
import type { ProbeFiles } from '../probeFiles'
import type { Reports } from '../reports'
import { reportPath } from '../reports'
import { SourceLink } from '../SourceLink'
import { FigureStrip } from './FigureStrip'
import { ProbeFilters } from './ProbeFilters'
import { probeRows } from './probeRows'
import { ProbesTable } from './ProbesTable'
import { ScoreScale } from './ScoreScale'
import type { LevelStarts, ProbeSetting } from './setting'
import { StatesLegend } from './StatesLegend'
import { useProbeTable } from './useProbeTable'
import './probes.css'

interface ProbesSectionProps {
  metrics: Metrics
  reports: Reports
  /** Null while the server does not publish the method: the probes still read, with less. */
  method: Method | null
  files: ProbeFiles
  starts: LevelStarts | null
}

/** Every probe with what it measured: the score scale, the three states in words, the figures
 *  of the report, then a table that sorts, filters, and opens on one probe. */
export function ProbesSection({ metrics, reports, method, files, starts }: ProbesSectionProps): ReactElement {
  const { nav } = useMethodShared()
  const all = useMemo(() => probeRows(metrics.probes, reports.probes, method?.labels ?? []), [metrics, reports, method])
  const open = nav.target.kind === 'probe' ? nav.target.key : null
  const table = useProbeTable(all, open)
  const setting = useMemo<ProbeSetting>(() => ({ starts, explorable: Boolean(method?.labelled), files }), [starts, method, files])

  if (all.length === 0) return <p className="nm-method__empty">No probe has a measured report yet.</p>
  return (
    <>
      <ScoreScale starts={starts} />
      <StatesLegend rows={all} />
      {method ? <FigureStrip method={method} /> : null}
      <p className="nm-note">
        {reports.probes ? (
          <>
            Every figure below is read from <SourceLink path={reportPath('probes')} />
            {reports.probes.run ? `, run ${reports.probes.run}` : ''}: one measurement of each probe, on a test split it never touched. Click a line to
            open a probe.
          </>
        ) : (
          'The evaluation report could not be read in full: only what the server publishes with each probe it serves is shown.'
        )}
      </p>
      <ProbeFilters all={all} table={table} />
      <ProbesTable
        rows={table.rows}
        sort={table.sort}
        open={open}
        setting={setting}
        onSort={table.sortBy}
        onToggle={(key) => nav.set(open === key ? { kind: 'section', section: 'probes' } : { kind: 'probe', key })}
      />
    </>
  )
}
