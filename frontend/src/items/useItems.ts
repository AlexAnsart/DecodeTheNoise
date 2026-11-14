import { useEffect, useState } from 'react'
import type { Item } from '../api/schema'
import { logger } from '../log/logger'
import { useItemStore } from '../source/mapServices'

const log = logger('items')

export interface ItemsState {
  items: Item[]
  loading: boolean
  error: string | null
}

/** The content of the given points, in order. `key` names the list, so a new list resets it. */
export function useItems(indices: number[], key: string): ItemsState {
  const store = useItemStore()
  const [state, setState] = useState<ItemsState>({ items: [], loading: false, error: null })

  useEffect(() => {
    if (indices.length === 0) {
      setState({ items: [], loading: false, error: null })
      return undefined
    }
    const known = indices.flatMap((index) => {
      const item = store.cached(index)
      return item ? [item] : []
    })
    if (known.length === indices.length) {
      setState({ items: known, loading: false, error: null })
      return undefined
    }
    const abort = new AbortController()
    setState((previous) => ({ items: previous.items, loading: true, error: null }))
    store
      .load(indices, abort.signal)
      .then((items) => setState({ items, loading: false, error: null }))
      .catch((error: unknown) => {
        if (abort.signal.aborted) return
        log.error('items could not be read', error)
        setState({ items: [], loading: false, error: 'The items could not be read.' })
      })
    return () => abort.abort()
    // The list is identified by its key: the array itself is rebuilt on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, store])

  return state
}

/** One item, read from the cache at once when it is there. */
export function useItem(index: number | null): Item | null {
  const { items } = useItems(index === null ? [] : [index], index === null ? 'none' : `one:${index}`)
  if (index === null) return null
  return items.find((item) => item.index === index) ?? null
}
