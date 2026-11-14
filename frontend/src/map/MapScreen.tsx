import { useMemo, useState } from 'react'
import type { ReactElement, ReactNode } from 'react'
import { createMapApi } from '../api/client'
import { MapApiContext, createMapServices } from '../source/mapServices'
import type { DataSource } from '../source/source'
import { MapView } from './MapView'
import { useMapData } from './useMapData'
import './map.css'

interface MapScreenProps {
  /** Where the map comes from: the demo dataset, or a workspace with its key. */
  source: DataSource
  /** The version a live map is known to have reached. When it moves, the map is read again
   *  and swapped in place: the camera, the colours and the selection stay. */
  version?: number
  /** Shown instead of the map while it has no point. */
  empty?: ReactNode
}

/** Loads the map of a source, then shows it. The loading and failure states are sentences,
 *  never a blank. */
export function MapScreen({ source, version, empty }: MapScreenProps): ReactElement {
  const { kind, base, apiKey } = source
  const api = useMemo(() => createMapApi({ kind, base, apiKey }), [kind, base, apiKey])
  const load = useMapData(api, version)
  // Points are only ever added to a live map. Fewer points means it was emptied: the indices
  // start again, so what was fetched and what was selected are let go.
  const points = load.status === 'ready' ? load.data.n : null
  const [track, setTrack] = useState({ points: 0, generation: 0 })
  if (points !== null && points !== track.points) {
    setTrack({ points, generation: points < track.points ? track.generation + 1 : track.generation })
  }
  const services = useMemo(
    () => createMapServices(api),
    // A new generation starts with nothing fetched.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [api, track.generation],
  )

  if (load.status === 'loading') {
    return (
      <div className="nm-screen-state" role="status">
        <strong>Reading the map…</strong>
        One point per item, placed by meaning.
      </div>
    )
  }
  if (load.status === 'error') {
    return (
      <div className="nm-screen-state nm-screen-state--error" role="alert">
        <strong>The map is not available.</strong>
        {load.message}
      </div>
    )
  }
  if (load.data.n === 0) {
    return (
      <>
        {empty ?? (
          <div className="nm-screen-state" role="status">
            <strong>This map has no point yet.</strong>
            Each item sent to it becomes a point.
          </div>
        )}
      </>
    )
  }
  return (
    <MapApiContext value={services}>
      <MapView key={`${load.data.build}:${track.generation}`} data={load.data} stale={load.stale} />
    </MapApiContext>
  )
}
