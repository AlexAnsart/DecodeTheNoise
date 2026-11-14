import type { CSSProperties, ReactElement } from 'react'

interface VoiceScaleProps {
  score: number
  /** Under it, the selection counts as one voice. */
  threshold: number
  /** Where 90% of the measured groups of independent actors score. */
  independent: [number, number]
  /** Where 90% of the measured groups written from one brief score. */
  oneBrief: [number, number]
}

const MARGIN = 0.04

function one(value: number): string {
  return value.toFixed(1)
}

/** The label of the marker hangs under it, and leans inward near an end so it stays readable. */
function labelShift(position: number): string {
  if (position < 18) return '0%'
  if (position > 82) return '-100%'
  return '-50%'
}

/** Where a selection sits between "one voice" and "separate voices": one track, the zone under
 *  the threshold, the band where independent actors score, and the selection's own mark. */
export function VoiceScale({ score, threshold, independent, oneBrief }: VoiceScaleProps): ReactElement {
  const low = Math.min(-2, score, oneBrief[0])
  const high = Math.max(independent[1], score)
  const pad = (high - low) * MARGIN
  const start = low - pad
  const span = high - low + 2 * pad
  const at = (value: number): number => Math.min(100, Math.max(0, ((value - start) / span) * 100))

  const mark = at(score)
  const bandLeft = at(independent[0])
  const words =
    `Score ${one(score)}, on a scale from one voice to separate voices. ` +
    `Under ${one(threshold)} counts as one voice. ` +
    `Independent actors score between ${one(independent[0])} and ${one(independent[1])}.`

  return (
    <div className="nm-voice-scale" role="img" aria-label={words}>
      <div className="nm-voice-scale__ends" aria-hidden>
        <span>One voice</span>
        <span>Separate voices</span>
      </div>
      <div className="nm-voice-scale__track" aria-hidden>
        {/* The tinted parts are clipped to the rounded track; the tick and the mark stand out of it. */}
        <span className="nm-voice-scale__fill">
          <span className="nm-voice-scale__zone" style={{ width: `${at(threshold)}%` }} />
          <span className="nm-voice-scale__band" style={{ left: `${bandLeft}%`, width: `${at(independent[1]) - bandLeft}%` }} />
        </span>
        <span className="nm-voice-scale__tick" style={{ left: `${at(threshold)}%` }} />
        <span className="nm-voice-scale__mark" style={{ left: `${mark}%` }} />
      </div>
      <div className="nm-voice-scale__here" aria-hidden>
        <span style={{ left: `${mark}%`, '--shift': labelShift(mark) } as CSSProperties}>
          This selection <b className="nm-num">{one(score)}</b>
        </span>
      </div>
      <ul className="nm-voice-scale__legend" aria-hidden>
        <li>
          <i className="nm-voice-scale__swatch nm-voice-scale__swatch--zone" />
          <span>
            Under <span className="nm-num">{one(threshold)}</span>: one voice
          </span>
        </li>
        <li>
          <i className="nm-voice-scale__swatch nm-voice-scale__swatch--band" />
          <span>
            Independent actors:{' '}
            <span className="nm-num">
              {one(independent[0])} to {one(independent[1])}
            </span>
          </span>
        </li>
      </ul>
    </div>
  )
}
