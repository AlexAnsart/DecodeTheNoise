/* Where a map comes from: the demo dataset, or the workspace of the person looking at it. */

export interface DataSource {
  kind: 'demo' | 'workspace'
  /** Prefix of every map route for this source. */
  base: string
  /** Sent as a bearer token; null for the demo, which is public. */
  apiKey: string | null
}

export const DEMO_SOURCE: DataSource = { kind: 'demo', base: '/api', apiKey: null }

export function workspaceSource(apiKey: string): DataSource {
  return { kind: 'workspace', base: '/api/v1', apiKey }
}
