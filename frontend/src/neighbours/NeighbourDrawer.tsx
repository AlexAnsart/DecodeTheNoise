import { X } from 'lucide-react'
import type { ReactElement } from 'react'
import { ItemList } from '../items/ItemList'
import type { MapData } from '../map/mapData'
import { plural } from '../text/format'
import './drawers.css'

interface NeighbourDrawerProps {
  data: MapData
  /** The selected point. */
  of: number
  /** Its neighbours by meaning still shown by the filters, nearest first. */
  neighbours: number[]
  onShow(index: number): void
  onOpen(index: number): void
  onRing(index: number | null): void
  onClose(): void
}

/** The nearest items by meaning of the selected one, measured on the full vectors and not on
 *  the layout: a long line on the map means the layout pulled two close items apart. */
export function NeighbourDrawer(props: NeighbourDrawerProps): ReactElement {
  const { data, of, neighbours, onShow, onOpen, onRing, onClose } = props
  return (
    <aside className="nm-drawer nm-drawer--neighbours" aria-label="Neighbours by meaning">
      <header className="nm-drawer__head">
        <h2 title="Nearest by meaning, measured before the layout. A long line means the map pulled two close items apart.">
          {plural(neighbours.length, 'neighbour', 'neighbours')}
        </h2>
        <button type="button" className="nm-drawer__icon" onClick={onClose} title="Close" aria-label="Close">
          <X size={15} aria-hidden />
        </button>
      </header>
      <ItemList data={data} indices={neighbours} listKey={`neighbours:${of}`} onShow={onShow} onOpen={onOpen} onRing={onRing} />
    </aside>
  )
}
