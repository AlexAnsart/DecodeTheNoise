import type { ReactElement } from 'react'
import { MapView } from './MapView'
import { useMapData } from './useMapData'
import './map.css'

/** Loads the map, then shows it. The loading and failure states are sentences, never a blank. */
export function MapScreen(): ReactElement {
  const load = useMapData()
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
  return <MapView key={load.data.build} data={load.data} />
}
