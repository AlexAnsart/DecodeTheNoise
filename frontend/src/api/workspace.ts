/* Workspaces and metrics: every call of the app shell to the backend. */

import { getJson, jsonBody, withKey } from './http'
import {
  batchAcceptedSchema,
  keyRotatedSchema,
  metricsSchema,
  publicConfigSchema,
  sampleSchema,
  workspaceCreatedSchema,
  workspaceInfoSchema,
} from './workspaceSchema'
import type {
  BatchAccepted,
  Metrics,
  PublicConfig,
  Sample,
  SamplePost,
  SettingsPatch,
  WorkspaceCreated,
  WorkspaceInfo,
} from './workspaceSchema'

const WORKSPACE = '/api/v1/workspace'

/** What the page needs before a workspace is open: the limits, and whether an LLM is set up. */
export function fetchConfig(signal?: AbortSignal): Promise<PublicConfig> {
  return getJson('/api/config', publicConfigSchema, { signal })
}

/** A new workspace. Its key is shown once: the server keeps only a hash. */
export function createWorkspace(): Promise<WorkspaceCreated> {
  return getJson('/api/workspaces', workspaceCreatedSchema, { method: 'POST' })
}

export function fetchWorkspace(apiKey: string, signal?: AbortSignal): Promise<WorkspaceInfo> {
  return getJson(WORKSPACE, workspaceInfoSchema, withKey({ signal }, apiKey))
}

export function patchSettings(apiKey: string, patch: SettingsPatch): Promise<WorkspaceInfo> {
  return getJson(`${WORKSPACE}/settings`, workspaceInfoSchema, withKey(jsonBody('PATCH', patch), apiKey))
}

/** Removes every item of the workspace. The key and the settings stay. */
export function emptyWorkspace(apiKey: string): Promise<WorkspaceInfo> {
  return getJson(`${WORKSPACE}/items`, workspaceInfoSchema, withKey({ method: 'DELETE' }, apiKey))
}

/** A new key for the workspace: the one given stops working. */
export async function rotateKey(apiKey: string): Promise<string> {
  const rotated = await getJson(`${WORKSPACE}/key`, keyRotatedSchema, withKey({ method: 'POST' }, apiKey))
  return rotated.api_key
}

/** Posts of the demo dataset in the shape the ingest route takes. */
export function fetchSample(count: number, signal?: AbortSignal): Promise<Sample> {
  return getJson(`/api/sample?count=${count}`, sampleSchema, { signal })
}

/** Stores posts through the public batch route: they are embedded in the background. */
export function sendBatch(apiKey: string, items: SamplePost[], signal?: AbortSignal): Promise<BatchAccepted> {
  return getJson('/api/v1/items/batch', batchAcceptedSchema, withKey(jsonBody('POST', { items }, signal), apiKey))
}

/** The probes served and the evaluation reports behind them. */
export function fetchMetrics(signal?: AbortSignal): Promise<Metrics> {
  return getJson('/api/metrics', metricsSchema, { signal })
}
