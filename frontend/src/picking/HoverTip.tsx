import { useLayoutEffect } from 'react'
import type { CSSProperties, ReactElement, RefObject } from 'react'
import type { LegendEntry } from '../colour/legend'
import { cssColour } from '../colour/palette'
import { useItem } from '../items/useItems'
import type { MapData } from '../map/mapData'
import { NO_VALUE, columnOf } from '../map/mapData'
import { formatDay } from '../text/format'
import './picking.css'

const EXCERPT_CHARS = 240

interface HoverTipProps {
  data: MapData
  index: number | null
  tip: RefObject<HTMLDivElement | null>
  /** Legend entry of the point under the current colouring, with the colouring's name. */
  entry: { title: string; entry: LegendEntry } | null
  /** Height read on the relief axis, when one is on. */
  score: { label: string; value: number } | null
  /** Set when the pointer is on a line to a neighbour of the selected point. */
  neighbourOfSelected: boolean
  onSettle(): void
}

function value(data: MapData, key: string, index: number): string | null {
  const column = columnOf(data, key)
  if (!column) return null
  const code = column.codes[index]
  return code === NO_VALUE ? null : column.names[code]
}

/** The tooltip box always exists, hidden, so it can follow the pointer without a render. */
export function HoverTip(props: HoverTipProps): ReactElement {
  const { data, index, tip, entry, score, neighbourOfSelected, onSettle } = props
  const item = useItem(index)
  const shown = index !== null && item !== null && item.index === index

  useLayoutEffect(() => {
    if (shown) onSettle()
  }, [shown, item, onSettle])

  const zone = shown ? value(data, 'zone', index) : null
  const meta = shown
    ? [value(data, 'post_type', index), item.created_at ? formatDay(item.created_at) : null, item.lang].filter(Boolean)
    : []
  const swatch = entry ? ({ '--swatch': cssColour(entry.entry.colour) } as CSSProperties) : undefined

  return (
    <div ref={tip} className="nm-tip" role="tooltip" hidden={!shown}>
      {shown ? (
        <>
          <div className="nm-tip__head">
            <strong>{value(data, 'actor', index) ?? item.actor_id}</strong>
            <span>{value(data, 'category', index)}</span>
          </div>
          <p className="nm-tip__text">
            {item.text.length > EXCERPT_CHARS ? `${item.text.slice(0, EXCERPT_CHARS)}…` : item.text}
          </p>
          {meta.length > 0 ? <p className="nm-tip__meta">{meta.join(' · ')}</p> : null}
          {zone && entry?.title !== 'Zone' ? <p className="nm-tip__line">Zone: {zone}</p> : null}
          {entry ? (
            <p className="nm-tip__line">
              <span className="nm-tip__swatch" style={swatch} aria-hidden />
              {entry.title}: {entry.entry.label}
            </p>
          ) : null}
          {score ? (
            <p className="nm-tip__line">
              {score.label}: {Math.round(score.value * 100)}% of the height
            </p>
          ) : null}
          {neighbourOfSelected ? <p className="nm-tip__note">A neighbour by meaning of the selected item</p> : null}
        </>
      ) : null}
    </div>
  )
}
