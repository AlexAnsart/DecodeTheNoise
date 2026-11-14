import { useState } from 'react'
import type { MapData } from '../map/mapData'
import type { Draft } from './groups'
import { carryDraft } from './groups'

/** The groups being composed, kept while the panel is closed. When a live map is read again,
 *  each group keeps the value it names. */
export function useDrafts(data: MapData): [Draft[] | null, (drafts: Draft[] | null) => void] {
  const [drafts, setDrafts] = useState<Draft[] | null>(null)
  const [seen, setSeen] = useState(data)
  if (seen !== data) {
    setSeen(data)
    if (drafts) setDrafts(drafts.map((draft) => carryDraft(draft, seen, data)))
  }
  return [drafts, setDrafts]
}
