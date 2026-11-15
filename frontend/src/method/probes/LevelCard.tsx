import type { ReactElement } from 'react'
import { formatCount } from '../../text/format'
import { formatNumber, formatRate } from '../figures'
import type { Level, LevelView } from './probeRows'
import { LEVEL_NAMES } from './probeRows'
import { RateLine } from './RateLine'

interface LevelCardProps {
  name: Level
  /** The score from which this level starts, the same for every probe; null while unknown. */
  from: number | null
  level: LevelView | null
  /** Why the probe has no such level, said in its place. */
  missing: string
}

/** What one level of one probe measured on the test split. */
export function LevelCard({ name, from, level, missing }: LevelCardProps): ReactElement {
  if (!level) {
    return (
      <section className={`nm-level nm-level--${name} nm-level--none`} aria-label={LEVEL_NAMES[name]}>
        <h4>{LEVEL_NAMES[name]}</h4>
        <p>{missing}</p>
      </section>
    )
  }
  return (
    <section className={`nm-level nm-level--${name}`} aria-label={LEVEL_NAMES[name]}>
      <h4>
        {LEVEL_NAMES[name]}
        {from !== null ? <span>from a score of {from}</span> : null}
      </h4>
      <dl>
        <RateLine label="Precision" hint="flagged posts that are a yes" rate={level.precision} bar />
        <RateLine label="Recall" hint="yes posts that are flagged" rate={level.recall} bar />
        <RateLine label="False-positive rate" hint="no posts that are flagged" rate={level.falsePositives} />
        <RateLine label="Prevalence" hint="posts that are a yes, estimated" rate={level.prevalence} />
      </dl>
      <p className="nm-level__counts nm-num">
        {level.flagRate !== null ? `${formatRate(level.flagRate)} of the test split is flagged` : 'The share flagged was not published'}
        {level.flagged !== null ? ` (${formatCount(level.flagged)} posts)` : ''}.
        {level.read !== null ? ` ${formatCount(level.read)} of them were read` : ''}
        {level.read !== null && level.positives !== null ? `, ${formatCount(level.positives)} settled as yes` : ''}
        {level.read !== null ? '.' : ''}
      </p>
      {level.baseRates.length > 0 ? (
        <table className="nm-level__rates nm-num">
          <caption>Precision this level would have if the label were this frequent</caption>
          <tbody>
            <tr>
              {level.baseRates.map(([base]) => (
                <th key={base} scope="col">
                  {formatRate(base)} of posts
                </th>
              ))}
            </tr>
            <tr>
              {level.baseRates.map(([base, precision]) => (
                <td key={base}>{formatRate(precision)}</td>
              ))}
            </tr>
          </tbody>
        </table>
      ) : null}
      {level.threshold !== null ? <p className="nm-level__cut nm-num">Cut on the raw output of the probe: {formatNumber(level.threshold)}</p> : null}
    </section>
  )
}
