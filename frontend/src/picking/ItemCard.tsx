import { Waypoints, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { ReactElement, RefObject } from 'react'
import { ItemSummary } from '../items/ItemSummary'
import { placeQuotes } from '../items/quotes'
import { useItems } from '../items/useItems'
import type { MapData } from '../map/mapData'
import { NO_VALUE, columnOf } from '../map/mapData'
import { PointProbes } from '../probes/PointProbes'
import { ReviewBlock } from '../probes/ReviewBlock'
import { quotesOf } from '../probes/reviewWords'
import { usePointReading } from '../probes/usePointReading'
import { usePointReview } from '../probes/usePointReview'
import { plural } from '../text/format'

interface ItemCardProps {
  data: MapData
  index: number
  card: RefObject<HTMLDivElement | null>
  neighbours: number
  /** The neighbour drawer was closed for this point: the card offers to open it again. */
  canOpenNeighbours: boolean
  onOpenNeighbours(): void
  onClose(): void
}

function name(data: MapData, key: string, index: number): string | null {
  const column = columnOf(data, key)
  const code = column?.codes[index]
  return column && code !== undefined && code !== NO_VALUE ? column.names[code] : null
}

/** The card of the selected point: what the item says, what the probes flag in it, then the
 *  LLM review. Its position is set after each frame, so it follows the camera. */
export function ItemCard(props: ItemCardProps): ReactElement {
  const { data, index, card, neighbours, canOpenNeighbours, onOpenNeighbours, onClose } = props
  const { items, loading, error } = useItems([index], `card:${index}`)
  const reading = usePointReading(data, index)
  const point = usePointReview(index, reading.status === 'ready' ? reading.reading.review : null)
  // The quote under the pointer, in a row of the review: it is brought out in the text.
  const [hover, setHover] = useState<{ of: number; quote: number } | null>(null)
  const active = hover && hover.of === index ? hover.quote : null
  const item = items.find((candidate) => candidate.index === index)
  const category = name(data, 'category', index)
  const zone = name(data, 'zone', index)
  // The words a completed review cites are marked and numbered inside the text itself.
  const read = point.ask.status !== 'running' && point.review?.status === 'done' ? point.review : null
  const marks = useMemo(() => (item && read ? placeQuotes(item.text, quotesOf(read)) : null), [item, read])

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
        {item ? <ItemSummary item={item} actor={name(data, 'actor', index)} clamp={null} marks={marks} active={active} /> : null}
        {!item && loading ? <p className="nm-item-state">Reading the item…</p> : null}
        {error ? <p className="nm-item-state nm-item-state--error">{error}</p> : null}
        <PointProbes probes={data.probes} state={reading} />
        {/* The review waits for the reading: it says whether the map already holds one. */}
        {item && reading.status !== 'loading' ? (
          <ReviewBlock
            point={point}
            probes={data.probes}
            marks={marks}
            active={active}
            onActive={(quote) => setHover(quote === null ? null : { of: index, quote })}
          />
        ) : null}
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
