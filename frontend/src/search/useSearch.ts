/* Search as you type: zones found in the browser at once, then items whose text holds the
   words, asked of the server once the typing settles. Typing lists results; it does not filter. */

import { useEffect, useMemo, useState } from 'react'
import { searchText } from '../api/client'
import { loadItems } from '../items/itemStore'
import { logger } from '../log/logger'
import type { MapData } from '../map/mapData'
import { columnOf } from '../map/mapData'
import { formatDay, plural } from '../text/format'

const log = logger('search')
const SETTLE_MS = 380
const MIN_CHARS = 2
const MAX_ITEMS = 12
const MAX_ZONES = 6
const EXCERPT = 90

export interface SearchHit {
  id: string
  kind: 'zone' | 'item'
  /** The point the camera goes to. */
  index: number
  label: string
  hint: string
}

export interface SearchState {
  /** The text the results answer, once the typing has settled. */
  settled: string
  hits: SearchHit[]
  /** One byte per point for the settled text; null until the server has answered. */
  mask: Uint8Array | null
  total: number
  loading: boolean
  error: string | null
}

function zoneHits(data: MapData, needle: string): SearchHit[] {
  const zones = columnOf(data, 'zone')
  if (!zones) return []
  const hits: SearchHit[] = []
  for (const zone of data.zones) {
    if (hits.length >= MAX_ZONES) break
    if (!`${zone.name} ${zone.words.join(' ')}`.toLowerCase().includes(needle)) continue
    const first = zones.codes.indexOf(zone.id)
    if (first < 0) continue
    hits.push({ id: `zone:${zone.id}`, kind: 'zone', index: first, label: zone.name, hint: `Zone · ${plural(zone.size, 'item', 'items')}` })
  }
  return hits
}

export function useSearch(data: MapData, text: string): SearchState {
  const [settled, setSettled] = useState('')
  const [answer, setAnswer] = useState<{ query: string; mask: Uint8Array; items: SearchHit[]; total: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => setSettled(text.trim()), SETTLE_MS)
    return () => clearTimeout(timer)
  }, [text])

  useEffect(() => {
    if (settled.length < MIN_CHARS) return undefined
    const abort = new AbortController()
    setError(null)
    searchText(settled, abort.signal)
      .then(async (mask) => {
        const found: number[] = []
        let total = 0
        for (let i = 0; i < mask.length; i += 1) {
          if (mask[i] !== 1) continue
          total += 1
          if (found.length < MAX_ITEMS) found.push(i)
        }
        const items = await loadItems(found, abort.signal)
        const rows = items.map((item) => ({
          id: `item:${item.index}`,
          kind: 'item' as const,
          index: item.index,
          label: item.text.length > EXCERPT ? `${item.text.slice(0, EXCERPT)}…` : item.text,
          hint: item.created_at ? formatDay(item.created_at) : 'No date',
        }))
        setAnswer({ query: settled, mask, items: rows, total })
      })
      .catch((cause: unknown) => {
        if (abort.signal.aborted) return
        log.error('the search failed', cause)
        setError('The search did not answer.')
      })
    return () => abort.abort()
  }, [settled])

  const zones = useMemo(() => (settled.length >= MIN_CHARS ? zoneHits(data, settled.toLowerCase()) : []), [data, settled])
  const current = answer && answer.query === settled ? answer : null
  return {
    settled,
    hits: [...zones, ...(current?.items ?? [])],
    mask: current?.mask ?? null,
    total: current?.total ?? 0,
    loading: settled.length >= MIN_CHARS && current === null && error === null,
    error,
  }
}
