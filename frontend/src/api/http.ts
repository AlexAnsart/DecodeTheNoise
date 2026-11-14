/* The request helpers every API module is built on. Nothing else in the app calls `fetch`. */

import type { z } from 'zod'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** The server's own words for a refusal: a sentence, or the first field a 422 names. */
function detailOf(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return null
  const { detail } = body
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail)) return null
  const first: unknown = detail[0]
  if (typeof first !== 'object' || first === null || !('msg' in first) || typeof first.msg !== 'string') return null
  const where = 'loc' in first && Array.isArray(first.loc) ? first.loc.filter((part) => part !== 'body').join('.') : ''
  return where ? `${where}: ${first.msg}` : first.msg
}

async function failure(response: Response): Promise<ApiError> {
  let detail: string | null = null
  try {
    detail = detailOf(await response.json())
  } catch {
    // The body was not JSON: the status text is all there is to say.
  }
  return new ApiError(response.status, detail ?? response.statusText)
}

/** Adds the workspace key to a request. A null key leaves the request as it is (the demo). */
export function withKey(init: RequestInit | undefined, apiKey: string | null): RequestInit {
  if (apiKey === null) return init ?? {}
  return { ...init, headers: { ...init?.headers, Authorization: `Bearer ${apiKey}` } }
}

export function jsonBody(method: 'POST' | 'PATCH', body: unknown, signal?: AbortSignal): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal }
}

/** The response when the server accepted the request; an `ApiError` with its reason otherwise. */
export async function send(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(path, init)
  if (!response.ok) throw await failure(response)
  return response
}

export async function getJson<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  return schema.parse(await (await send(path, init)).json())
}

export async function getBytes(path: string, init?: RequestInit): Promise<ArrayBuffer> {
  return (await send(path, init)).arrayBuffer()
}
