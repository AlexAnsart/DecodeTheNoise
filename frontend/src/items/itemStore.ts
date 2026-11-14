/* Item content is not in the map: it is fetched by point index, in pages, and kept a while.
   One store per map, since a point index means another item in another map. */

import type { MapApi } from '../api/client'
import type { Item } from '../api/schema'

const CACHE_SIZE = 600
const PAGE = 200

export interface ItemStore {
  cached(index: number): Item | undefined
  /** Items in the order asked. Only the ones not seen recently are requested. */
  load(indices: number[], signal?: AbortSignal): Promise<Item[]>
}

export function createItemStore(api: MapApi): ItemStore {
  const cache = new Map<number, Item>()

  const remember = (item: Item): void => {
    cache.delete(item.index)
    cache.set(item.index, item)
    if (cache.size > CACHE_SIZE) {
      const oldest = cache.keys().next().value
      if (oldest !== undefined) cache.delete(oldest)
    }
  }

  return {
    cached: (index) => cache.get(index),
    async load(indices, signal) {
      const missing = indices.filter((index) => !cache.has(index))
      for (let start = 0; start < missing.length; start += PAGE) {
        const page = await api.items(missing.slice(start, start + PAGE), signal)
        page.forEach(remember)
      }
      return indices.flatMap((index) => {
        const item = cache.get(index)
        return item ? [item] : []
      })
    },
  }
}
