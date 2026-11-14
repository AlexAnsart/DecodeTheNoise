import { Waypoints, X } from 'lucide-react'
import type { ReactElement, ReactNode, RefObject } from 'react'
import type { Item } from '../api/schema'
import { ItemSummary } from '../items/ItemSummary'
import { useItems } from '../items/useItems'
import type { MapData } from '../map/mapData'
import { NO_VALUE, columnOf } from '../map/mapData'
import { plural } from '../text/format'

interface ItemCardProps {
  data: MapData
  index: number
  card: RefObject<HTMLDivElement | null>
  neighbours: number
  /** The neighbour drawer was closed for this point: the card offers to open it again. */
  canOpenNeighbours: boolean
  onOpenNeighbours(): void
  /** The verdicts on the item or on the account behind it, each with its evidence. */
  verdicts(item: Item): ReactNode
  onClose(): void
}

function name(data: MapData, key: string, index: number): string | null {
  const column = columnOf(data, key)
  const code = column?.codes[index]
  return column && code !== undefined && code !== NO_VALUE ? column.names[code] : null
}

/** The card of the selected point. Its position is set after each frame, so it follows the camera. */
export function ItemCard(props: ItemCardProps): ReactElement {
  const { data, index, card, neighbours, canOpenNeighbours, onOpenNeighbours, verdicts, onClose } = props
  const { items, loading, error } = useItems([index], `card:${index}`)
  const item = items.find((candidate) => candidate.index === index)
  const category = name(data, 'category', index)
  const zone = name(data, 'zone', index)

  return (
    <div ref={card} className="nm-card" role="dialog" aria-label="Selected item">
      <header className="nm-card__head">
        {category ? <span className="nm-pill">{category}</span> : null}
        {zone ? <span className="nm-chip" title={`Zone: ${zone}`}>{zone}</span> : null}
        <button type="button" className="nm-card__close" onClick={onClose} title="Close" aria-label="Close">
          <X size={13} aria-hidden />
        </button>
      </header>
      <div className="nm-card__body">
        {item ? <ItemSummary item={item} actor={name(data, 'actor', index)} clamp={null} /> : null}
        {item ? verdicts(item) : null}
        {!item && loading ? <p className="nm-item-state">Reading the item…</p> : null}
        {error ? <p className="nm-item-state nm-item-state--error">{error}</p> : null}
      </div>
      {canOpenNeighbours && neighbours > 0 ? (
        <footer className="nm-card__foot">
          <button type="button" className="nm-btn-secondary nm-btn-small" onClick={onOpenNeighbours}>
            <Waypoints size={12} aria-hidden />
            {plural(neighbours, 'neighbour', 'neighbours')}
          </button>
        </footer>
      ) : null}
    </div>
  )
}
