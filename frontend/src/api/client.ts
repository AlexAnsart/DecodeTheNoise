/* The calls a map makes to the backend, bound to the source the map comes from: the demo
   dataset under `/api`, or a workspace under `/api/v1` with its key. */

import type { DataSource } from '../source/source'
import { getBytes, getJson, jsonBody, send, withKey } from './http'
import { bufferBytes, readCounted } from './mapBytes'
import type { Progress } from './mapBytes'
import { reviewSchema, selectionReviewSchema } from './reviewSchema'
import type { Review, SelectionReview } from './reviewSchema'
import { analysisSchema, healthSchema, itemsResponseSchema, manifestSchema, pointReadingSchema } from './schema'
import type { Analysis, Health, Item, Manifest, PointReading } from './schema'
import { voicesSchema } from './voicesSchema'
import type { Voices } from './voicesSchema'

export { ApiError } from './http'

export interface MapApi {
  source: DataSource
  manifest(signal?: AbortSignal): Promise<Manifest>
  /** The typed arrays of the map as `manifest` describes it. With `onProgress`, they are read
   *  as they arrive and the bytes received are reported. */
  buffers(manifest: Manifest, signal?: AbortSignal, onProgress?: Progress): Promise<ArrayBuffer>
  items(indices: number[], signal?: AbortSignal): Promise<Item[]>
  /** Places a pasted text, or the page behind a pasted link, on the map. */
  analyze(input: { text: string } | { url: string }, signal?: AbortSignal): Promise<Analysis>
  /** One byte per point: 1 where the text holds every word of the query. */
  searchText(query: string, signal?: AbortSignal): Promise<Uint8Array>
  /** One float per point: cosine between the item and the text. */
  similarityToText(query: string, signal?: AbortSignal): Promise<Float32Array>
  /** One float per point: cosine between the item and the mean direction of the given points. */
  similarityToItems(indices: number[], signal?: AbortSignal): Promise<Float32Array>
  /** One float per point: the score of a probe, NaN where the probe does not read the point. */
  scores(probeKey: string, signal?: AbortSignal): Promise<Float32Array>
  /** What the probes and the review say of one point. */
  reading(index: number, signal?: AbortSignal): Promise<PointReading>
  /** Has the LLM review one point now. Slow (seconds), and limited: a refusal comes as an
   *  `ApiError` with its sentence (429 at the limit, 503 without an LLM). */
  review(index: number, signal?: AbortSignal): Promise<Review>
  /** Reviews a group of points (5,000 at most): what the probes measure on it, then what the
   *  LLM reads in a sample of its posts. Slow: about ten seconds. */
  reviewSelection(indices: number[], signal?: AbortSignal): Promise<SelectionReview>
  /** Whether the actors behind the given points each have a voice of their own. */
  voices(indices: number[], signal?: AbortSignal): Promise<Voices>
}

export function fetchHealth(): Promise<Health> {
  return getJson('/api/health', healthSchema)
}

export function createMapApi(source: DataSource): MapApi {
  const { base, apiKey } = source
  // A workspace changes under the same URL: its answers are never taken from the browser cache.
  const fresh: RequestInit = source.kind === 'workspace' ? { cache: 'no-store' } : {}
  const get = (signal?: AbortSignal): RequestInit => withKey({ ...fresh, signal }, apiKey)
  const post = (body: unknown, signal?: AbortSignal): RequestInit => withKey(jsonBody('POST', body, signal), apiKey)
  const text = (value: string): string => encodeURIComponent(value)

  return {
    source,
    manifest: (signal) => getJson(`${base}/map`, manifestSchema, get(signal)),
    buffers: async (manifest, signal, onProgress) => {
      // A build never changes under its name; a live map is named by its version.
      const stamp = manifest.live ? `v=${manifest.version}` : `b=${text(manifest.build)}`
      const path = `${base}/map/buffers?${stamp}`
      if (!onProgress) return getBytes(path, get(signal))
      return readCounted(await send(path, get(signal)), bufferBytes(manifest), onProgress)
    },
    items: async (indices, signal) => (await getJson(`${base}/map/items`, itemsResponseSchema, post({ indices }, signal))).items,
    analyze: (input, signal) => {
      const body = 'url' in input ? { text: null, url: input.url } : { text: input.text, url: null }
      return getJson(`${base}/analyze`, analysisSchema, post(body, signal))
    },
    searchText: async (query, signal) => new Uint8Array(await getBytes(`${base}/search/text?q=${text(query)}`, get(signal))),
    similarityToText: async (query, signal) => new Float32Array(await getBytes(`${base}/similarity?q=${text(query)}`, get(signal))),
    similarityToItems: async (indices, signal) => new Float32Array(await getBytes(`${base}/similarity/items`, post({ indices }, signal))),
    scores: async (probeKey, signal) => new Float32Array(await getBytes(`${base}/map/scores/${text(probeKey)}`, get(signal))),
    reading: (index, signal) => getJson(`${base}/map/reading/${index}`, pointReadingSchema, get(signal)),
    review: (index, signal) => getJson(`${base}/map/review/${index}`, reviewSchema, withKey({ method: 'POST', signal }, apiKey)),
    reviewSelection: (indices, signal) => getJson(`${base}/review/selection`, selectionReviewSchema, post({ indices }, signal)),
    voices: (indices, signal) => getJson(`${base}/voices`, voicesSchema, post({ indices }, signal)),
  }
}
