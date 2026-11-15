import type { ReactElement } from 'react'
import { StateChip } from '../StateChip'
import { PROBE_STATES, stateWord } from '../words'
import type { ProbeRow } from './probeRows'

/** The three states a probe can end in, each in words, with how many probes are in it. */
export function StatesLegend({ rows }: { rows: ProbeRow[] }): ReactElement {
  return (
    <dl className="nm-states-legend">
      {PROBE_STATES.map((state) => {
        const count = rows.filter((row) => row.state === state).length
        return count > 0 ? (
          <div key={state}>
            <dt>
              <StateChip state={state} />
              <b className="nm-num">{count}</b>
            </dt>
            <dd>{stateWord(state).meaning}</dd>
          </div>
        ) : null
      })}
    </dl>
  )
}
