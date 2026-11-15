import type { ReactElement } from 'react'
import type { LevelStarts } from './setting'

/** The one scale every probe scores on, and what a level means. */
export function ScoreScale({ starts }: { starts: LevelStarts | null }): ReactElement {
  if (!starts) {
    return (
      <p className="nm-note">
        Every probe scores on one scale, cut in two levels: possible, then probable. Where each level starts is read from the server, which has not
        answered yet.
      </p>
    )
  }
  const { possible, probable } = starts
  return (
    <div className="nm-scale">
      <div className="nm-scale__track" role="img" aria-label={`A score from 0 to 1: not flagged under ${possible}, possible from ${possible}, probable from ${probable}`}>
        <span style={{ width: `${100 * possible}%` }}>Not flagged</span>
        <span className="nm-scale__possible" style={{ width: `${100 * (probable - possible)}%` }}>
          Possible
        </span>
        <span className="nm-scale__probable" style={{ width: `${100 * (1 - probable)}%` }}>
          Probable
        </span>
      </div>
      <div className="nm-scale__marks nm-num" aria-hidden>
        <span style={{ left: 0 }}>0</span>
        <span style={{ left: `${100 * possible}%` }}>{possible}</span>
        <span style={{ left: `${100 * probable}%` }}>{probable}</span>
        <span style={{ left: '100%' }}>1</span>
      </div>
      <p>
        Every probe scores on this one scale: <strong>{possible}</strong> is where <em>possible</em> starts and <strong>{probable}</strong> where{' '}
        <em>probable</em> starts, for every probe. The score is a position against the probe's own thresholds, not a probability. What a level is
        worth is the precision it measured on posts the probe never saw: that is the number shown beside every hit, and in the table below.
      </p>
      <p>
        A probe can have one level only. When its two cuts fall at the same place, or when its possible level was withdrawn, it has no possible
        level: for that probe a score under {probable} has no name, and nothing is flagged from it. When no cut reached the precision asked of
        probable, the probe stops at possible.
      </p>
    </div>
  )
}
