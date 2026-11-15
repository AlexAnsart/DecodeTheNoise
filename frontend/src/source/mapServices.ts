/* What the parts of a map share: the API bound to its source, and what was already fetched.
   Given through a context, so no component of the map has to be told where its data lives. */

import { createContext, useContext } from 'react'
import type { MapApi } from '../api/client'
import type { ItemStore } from '../items/itemStore'
import { createItemStore } from '../items/itemStore'
import type { ReviewStore } from '../probes/reviewStore'
import { createReviewStore } from '../probes/reviewStore'
import type { ScoreStore } from '../probes/scoreStore'
import { createScoreStore } from '../probes/scoreStore'

export interface MapServices {
  api: MapApi
  items: ItemStore
  scores: ScoreStore
  reviews: ReviewStore
}

export const MapApiContext = createContext<MapServices | null>(null)

/** Fresh stores for one map: what one map fetched says nothing of another. */
export function createMapServices(api: MapApi): MapServices {
  return { api, items: createItemStore(api), scores: createScoreStore(api), reviews: createReviewStore(api) }
}

function useMapServices(): MapServices {
  const services = useContext(MapApiContext)
  if (!services) throw new Error('This component belongs inside a map: no data source is set.')
  return services
}

export function useMapApi(): MapApi {
  return useMapServices().api
}

export function useItemStore(): ItemStore {
  return useMapServices().items
}

export function useScoreStore(): ScoreStore {
  return useMapServices().scores
}

export function useReviewStore(): ReviewStore {
  return useMapServices().reviews
}
