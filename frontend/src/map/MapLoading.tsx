import type { ReactElement } from 'react'
import { formatCount } from '../text/format'
import type { MapProgress } from './useMapData'

/** What the page says while a map is read for the first time. A large map takes seconds to
 *  arrive: one line says what is coming, a thin bar says how far it is. */
export function MapLoading({ progress }: { progress: MapProgress | null }): ReactElement {
  const share = progress?.share ?? null
  const percent = share === null ? null : Math.min(100, Math.round(share * 100))
  return (
    <div className="nm-screen-state">
      <strong role="status">{progress ? `Reading the map: ${formatCount(progress.points)} points` : 'Reading the map…'}</strong>
      {progress && percent !== null ? (
        <>
          <div className="nm-load-bar" role="progressbar" aria-label="Share of the map received" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
            <i style={{ width: `${percent}%` }} />
          </div>
          <span className="nm-num">
            {percent < 100 ? `${percent}% received` : 'Received. Drawing the points…'}
          </span>
        </>
      ) : (
        'One point per item, placed by meaning.'
      )}
    </div>
  )
}
