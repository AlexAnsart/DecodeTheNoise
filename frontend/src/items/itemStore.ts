/* Item content is not in the map: it is fetched by point index, in pages, and kept a while. */

import { fetchItems } from '../api/client'
import type { Item } from '../api/schema'

const CACHE_SIZE = 600
const PAGE = 200

const cache = new Map<number, Item>()

function remember(item: Item): void {
  cache.delete(item.index)
  cache.set(item.index, item)
  if (cache.size > CACHE_SIZE) {
    const oldest = cache.keys().next().value
    if (oldest !== undefined) cache.delete(oldest)
  }
}

export function cachedItem(index: number): Item | undefined {
  return cache.get(index)
}

/** Items in the order asked. Only the ones not seen recently are requested. */
export async function loadItems(indices: number[], signal?: AbortSignal): Promise<Item[]> {
  const missing = indices.filter((index) => !cache.has(index))
  for (let start = 0; start < missing.length; start += PAGE) {
    const page = await fetchItems(missing.slice(start, start + PAGE), signal)
    page.forEach(remember)
  }
  return indices.flatMap((index) => {
    const item = cache.get(index)
    return item ? [item] : []
  })
}
