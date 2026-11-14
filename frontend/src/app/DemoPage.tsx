import type { ReactElement } from 'react'
import { MapScreen } from '../map/MapScreen'
import { ApiPromo } from '../promo/ApiPromo'
import { DEMO_SOURCE } from '../source/source'
import { Tour } from '../tour/Tour'
import type { TourControl } from '../tour/useTour'

/** The demo dataset: the map at once, the tour on a first visit, then the way to one's own map. */
export function DemoPage({ tour }: { tour: TourControl }): ReactElement {
  return (
    <div className="nm-demo">
      <MapScreen source={DEMO_SOURCE} />
      {/* One thing at a time: the card waits for the tour to end. */}
      {tour.active ? <Tour onEnd={tour.end} /> : <ApiPromo />}
    </div>
  )
}
