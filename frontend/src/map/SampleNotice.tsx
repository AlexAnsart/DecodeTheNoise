import type { ReactElement } from 'react'
import { formatCount } from '../text/format'
import type { Sampling } from './useSoftwareGuard'

/** Points a browser without a GPU draws in a second. Measured in Edge with hardware
 *  acceleration off, on the 500,000-point map: 32 s for the full cloud. */
const POINTS_PER_SECOND = 16_000

/** Said near the point count where the browser draws in software and the map is large: a
 *  sample of the points is drawn, the counts elsewhere still count the whole map, and one
 *  button draws everything, after saying how long the page will stop answering. */
export function SampleNotice({ sampling }: { sampling: Sampling }): ReactElement {
  const { sample, total, state, showAll, showSample } = sampling
  const seconds = Math.max(5, Math.round(total / POINTS_PER_SECOND / 5) * 5)
  return (
    <div className="nm-sample" role="status">
      {state === 'sample' ? (
        <>
          <span>
            No GPU acceleration in this browser: showing {formatCount(sample)} of {formatCount(total)} points.
          </span>
          <button
            type="button"
            className="nm-sample__switch"
            onClick={showAll}
            // The legend has a "Show all" of its own: this one is named by what it shows.
            aria-label={`Show all ${formatCount(total)} points`}
            title="Draws every point. Without a GPU the page stops answering while it draws."
          >
            Show all
          </button>
        </>
      ) : null}
      {state === 'drawing' ? (
        <span>
          Drawing {formatCount(total)} points in software: this takes about {seconds} s, and the page does not answer meanwhile.
        </span>
      ) : null}
      {state === 'all' ? (
        <>
          <span>No GPU acceleration in this browser: all {formatCount(total)} points are drawn, and the map answers slowly.</span>
          <button type="button" className="nm-sample__switch" onClick={showSample} aria-label={`Show ${formatCount(sample)} points`}>
            Show {formatCount(sample)}
          </button>
        </>
      ) : null}
    </div>
  )
}
