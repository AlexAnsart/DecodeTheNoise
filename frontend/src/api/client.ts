/* Every HTTP call to the backend goes through this module. */

import type { z } from 'zod'
import {
  analysisSchema,
  healthSchema,
  itemsResponseSchema,
  manifestSchema,
  metricsResponseSchema,
  swarmLayerSchema,
  swarmSchema,
} from './schema'
import type { Analysis, DetectorMetrics, Health, Item, Manifest, Swarm, SwarmLayer } from './schema'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function failure(response: Response): Promise<ApiError> {
  let detail = response.statusText
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string') {
      detail = body.detail
    }
  } catch {
    // The body was not JSON: the status text is all there is to say.
  }
  return new ApiError(response.status, detail)
}

async function getJson<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) throw await failure(response)
  return schema.parse(await response.json())
}

async function getBytes(path: string, init?: RequestInit): Promise<ArrayBuffer> {
  const response = await fetch(path, init)
  if (!response.ok) throw await failure(response)
  return response.arrayBuffer()
}

function postJson(body: unknown, signal?: AbortSignal): RequestInit {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal }
}

export function fetchHealth(): Promise<Health> {
  return getJson('/api/health', healthSchema)
}

export function fetchManifest(): Promise<Manifest> {
  return getJson('/api/map', manifestSchema)
}

export function fetchBuffers(build: string): Promise<ArrayBuffer> {
  return getBytes(`/api/map/buffers?b=${encodeURIComponent(build)}`)
}

export async function fetchItems(indices: number[], signal?: AbortSignal): Promise<Item[]> {
  const body = await getJson('/api/items', itemsResponseSchema, postJson({ indices }, signal))
  return body.items
}

/** Places a pasted text, or the page behind a pasted link, on the map. */
export function analyze(input: { text: string } | { url: string }, signal?: AbortSignal): Promise<Analysis> {
  const body = 'url' in input ? { text: null, url: input.url } : { text: input.text, url: null }
  return getJson('/api/analyze', analysisSchema, postJson(body, signal))
}

/** The swarm layer of the map, or null when the map has none that was measured. */
export async function fetchSwarmLayer(): Promise<SwarmLayer | null> {
  try {
    return await getJson('/api/swarms', swarmLayerSchema)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

/** One swarm with its evidence. */
export function fetchSwarm(id: number, signal?: AbortSignal): Promise<Swarm> {
  return getJson(`/api/swarms/${id}`, swarmSchema, { signal })
}

/** The evaluation report of every detector the product shows. */
export async function fetchMetrics(signal?: AbortSignal): Promise<DetectorMetrics[]> {
  const body = await getJson('/api/metrics', metricsResponseSchema, { signal })
  return body.detectors
}

/** One byte per point: 1 where the text holds every word of the query. */
export async function searchText(query: string, signal?: AbortSignal): Promise<Uint8Array> {
  return new Uint8Array(await getBytes(`/api/search/text?q=${encodeURIComponent(query)}`, { signal }))
}

/** One float per point: cosine between the item and the text. */
export async function similarityToText(query: string, signal?: AbortSignal): Promise<Float32Array> {
  return new Float32Array(await getBytes(`/api/similarity?q=${encodeURIComponent(query)}`, { signal }))
}

/** One float per point: cosine between the item and the mean direction of the given points. */
export async function similarityToItems(indices: number[], signal?: AbortSignal): Promise<Float32Array> {
  return new Float32Array(await getBytes('/api/similarity/items', postJson({ indices }, signal)))
}
