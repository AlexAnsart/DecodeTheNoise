import type { ReactElement } from 'react'
import type { ProbeReading } from '../api/schema'
import { LEVEL_START, LEVEL_WORD, formatScore, measureWords } from './levels'

/** One probe that flagged the item: the level it reached, and what that level measured to be
 *  worth on held-out posts. A level, never a statement of fact. */
export function ProbeVerdict({ reading }: { reading: ProbeReading }): ReactElement {
  return (
    <div className={`nm-verdict nm-verdict--${reading.level}`} role="group" aria-label={`${LEVEL_WORD[reading.level]}: ${reading.label}`}>
      <div className="nm-verdict__head">
        <span className="nm-verdict__level">{LEVEL_WORD[reading.level]}</span>
        <span className="nm-verdict__label">{reading.label}</span>
        <span className="nm-verdict__score nm-num" title={`Score of the probe, from 0 to 1. This level starts at ${LEVEL_START[reading.level]}.`}>
          {formatScore(reading.score)}
        </span>
      </div>
      <p className="nm-verdict__measure">
        Measured at this level: {measureWords(reading.reliability)}. <a href="/method#probes">How it is measured</a>
      </p>
    </div>
  )
}
