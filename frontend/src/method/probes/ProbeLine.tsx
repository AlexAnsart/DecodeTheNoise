import { ChevronRight } from 'lucide-react'
import type { ReactElement } from 'react'
import { formatInterval, formatLift, formatShare } from '../figures'
import { StateChip } from '../StateChip'
import { ProbeDetail } from './ProbeDetail'
import type { LevelView, ProbeRow } from './probeRows'
import { widestLevel } from './probeRows'
import type { ProbeSetting } from './setting'

export const PROBE_COLUMNS = 7

function Precision({ level }: { level: LevelView | null }): ReactElement {
  const precision = level?.precision
  if (!precision) return <td className="nm-num nm-ptable__none">–</td>
  return (
    <td className="nm-num">
      <strong>{formatShare(precision.value)}</strong>
      {precision.low !== null && precision.high !== null ? <span>{formatInterval(precision.low, precision.high)}</span> : null}
    </td>
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
  const widest = widestLevel(row)
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
        <Precision level={row.possible} />
        <Precision level={row.probable} />
        <td className="nm-num">{formatShare(widest?.recall?.value ?? null)}</td>
        <td className="nm-num">{formatShare(widest?.flagRate ?? null)}</td>
        <td className="nm-num">{formatLift(row.lift)}</td>
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
