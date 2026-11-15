import { ChevronRight } from 'lucide-react'
import type { ReactElement } from 'react'
import { formatInterval, formatLift, formatShare } from '../figures'
import { StateChip } from '../StateChip'
import { absenceOf } from './absence'
import { ProbeDetail } from './ProbeDetail'
import type { Level, ProbeRow } from './probeRows'
import { LEVELS } from './probeRows'
import type { ProbeSetting } from './setting'

/** The columns of one level: precision, recall, share flagged. */
export const LEVEL_CELLS = 3

/** Probe, state, the levels, ranking. */
export const PROBE_COLUMNS = 3 + LEVELS.length * LEVEL_CELLS

/** One level of a probe: its three figures, or in their place why the probe has no such level. */
function LevelCells({ row, level, setting }: { row: ProbeRow; level: Level; setting: ProbeSetting }): ReactElement {
  const view = row[level]
  if (!view) {
    const absence = absenceOf(row, level, setting.starts)
    return (
      <td colSpan={LEVEL_CELLS} className={`nm-ptable__group nm-ptable__absent${absence ? '' : ' nm-ptable__none'}`} title={absence?.long}>
        {absence?.short ?? '–'}
      </td>
    )
  }
  const { precision } = view
  return (
    <>
      <td className="nm-num nm-ptable__group">
        <strong>{formatShare(precision?.value ?? null)}</strong>
        {precision && precision.low !== null && precision.high !== null ? <span>{formatInterval(precision.low, precision.high)}</span> : null}
      </td>
      <td className="nm-num">{formatShare(view.recall?.value ?? null)}</td>
      <td className="nm-num">{formatShare(view.flagRate)}</td>
    </>
  )
}

interface ProbeLineProps {
  row: ProbeRow
  open: boolean
  setting: ProbeSetting
  onToggle(): void
}

/** One probe of the table: its line, and under it what it measured when it is opened. */
export function ProbeLine({ row, open, setting, onToggle }: ProbeLineProps): ReactElement {
  const detail = `probe-detail-${row.key}`
  return (
    <>
      <tr id={`probe-${row.key}`} className={`nm-ptable__line${open ? ' is-open' : ''}`} onClick={onToggle}>
        <th scope="row">
          <button
            type="button"
            className="nm-ptable__name"
            aria-expanded={open}
            aria-controls={detail}
            onClick={(event) => {
              // The line toggles too: one click must not count twice.
              event.stopPropagation()
              onToggle()
            }}
          >
            <ChevronRight size={13} aria-hidden />
            <span>
              <strong>{row.name}</strong>
              <code>{row.key}</code>
            </span>
          </button>
        </th>
        <td>
          <StateChip state={row.state} />
          {row.family ? <span className="nm-ptable__family">{row.family}</span> : null}
        </td>
        {LEVELS.map((level) => (
          <LevelCells key={level} row={row} level={level} setting={setting} />
        ))}
        <td className="nm-num nm-ptable__group">{formatLift(row.lift)}</td>
      </tr>
      {open ? (
        <tr id={detail} className="nm-ptable__detail">
          <td colSpan={PROBE_COLUMNS}>
            <ProbeDetail row={row} setting={setting} />
          </td>
        </tr>
      ) : null}
    </>
  )
}
