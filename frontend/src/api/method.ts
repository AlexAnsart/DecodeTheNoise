/* The method page's calls: what the product was built from, and the posts the annotators read. */

import { getJson } from './http'
import { labelledPageSchema, methodSchema } from './methodSchema'
import type { LabelledPage, Method } from './methodSchema'

const METHOD = '/api/method'

/** Every labelled post with its readings, as JSON lines. */
export const LABELLED_DOWNLOAD = `${METHOD}/labelled.jsonl`

/** The filters of the labelled posts. An empty value does not filter. */
export interface LabelledQuery {
  label: string
  answer: string
  split: string
  round: string
  /** `annotation` or `second reader`. */
  kind: string
  /** A probe, with how it stands against the annotation of its own label. */
  probe: string
  level: string
  /** Words the text must hold. */
  q: string
  offset: number
  limit: number
}

export function fetchMethod(signal?: AbortSignal): Promise<Method> {
  return getJson(METHOD, methodSchema, { signal })
}

export function fetchLabelled(query: LabelledQuery, signal?: AbortSignal): Promise<LabelledPage> {
  const params = new URLSearchParams()
  for (const [name, value] of Object.entries(query)) {
    if (value !== '' && value !== null) params.set(name, String(value))
  }
  return getJson(`${METHOD}/labelled?${params}`, labelledPageSchema, { signal })
}

/** Where a figure of the report is served. */
export function figureUrl(name: string): string {
  return `${METHOD}/figures/${encodeURIComponent(name)}`
}
