import { LocateFixed } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { MapData } from '../map/mapData'
import { NO_VALUE, columnOf } from '../map/mapData'
import { ItemSummary } from './ItemSummary'
import { useItems } from './useItems'

const PAGE = 30

interface ItemListProps {
  data: MapData
  indices: number[]
  /** Names the list: a new key starts again from the first page. */
  listKey: string
  onShow(index: number): void
  onOpen(index: number): void
  onRing(index: number | null): void
}

function actorOf(data: MapData, index: number): string | null {
  const column = columnOf(data, 'actor')
  const code = column?.codes[index]
  return column && code !== undefined && code !== NO_VALUE ? column.names[code] : null
}

/** Items as cards, read by pages as the end of the list scrolls into view. */
export function ItemList({ data, indices, listKey, onShow, onOpen, onRing }: ItemListProps): ReactElement {
  const [paged, setPaged] = useState({ key: listKey, limit: PAGE })
  const limit = paged.key === listKey ? paged.limit : PAGE
  const sentinel = useRef<HTMLDivElement>(null)
  const page = indices.slice(0, limit)
  const { items, loading, error } = useItems(page, `${listKey}:${limit}`)
  const more = limit < indices.length

  useEffect(() => {
    const node = sentinel.current
    if (!node || !more) return undefined
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) setPaged({ key: listKey, limit: limit + PAGE })
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [more, limit, listKey, items.length])

  return (
    <div className="nm-list" onPointerLeave={() => onRing(null)}>
      {items.map((item) => (
        <article
          key={item.index}
          className="nm-list__card"
          onPointerEnter={() => onRing(item.index)}
        >
          <button type="button" className="nm-list__open" onClick={() => onOpen(item.index)} title="Select this item on the map">
            <ItemSummary item={item} actor={actorOf(data, item.index)} clamp={6} />
          </button>
          <button
            type="button"
            className="nm-list__show"
            onClick={() => onShow(item.index)}
            title="Show on the map"
            aria-label="Show on the map"
          >
            <LocateFixed size={13} aria-hidden />
          </button>
        </article>
      ))}
      {loading ? <p className="nm-item-state">Reading the items…</p> : null}
      {error ? <p className="nm-item-state nm-item-state--error">{error}</p> : null}
      {more ? <div ref={sentinel} className="nm-list__more" /> : null}
    </div>
  )
}
