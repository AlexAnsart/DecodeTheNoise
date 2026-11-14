/* What a workspace is doing, in short words. Pure: every number comes from the server. */

import type { WorkspaceInfo } from '../api/workspaceSchema'
import { formatCount, plural } from '../text/format'

const SECONDS_STEP = 5

export interface Embedding {
  done: number
  total: number
}

/** The batch being embedded and how far it is; null when nothing waits. */
export function embeddingOf(info: WorkspaceInfo): Embedding | null {
  if (info.pending === 0) return null
  // A batch never counts fewer posts than still wait.
  const total = Math.max(info.ingest.batch, info.pending)
  return { done: total - info.pending, total }
}

/** The server's estimate in words: seconds by steps of five, then minutes. */
export function etaWords(seconds: number | null): string {
  if (seconds === null) return 'estimating the time left…'
  const rounded = Math.max(SECONDS_STEP, Math.round(seconds / SECONDS_STEP) * SECONDS_STEP)
  if (rounded < 60) return `about ${rounded} s left`
  return `about ${Math.max(1, Math.round(seconds / 60))} min left`
}

/** Where a batch stands in time: the estimate, or why there is none to give. */
export function timeWords(info: WorkspaceInfo, live: boolean): string {
  if (info.ingest.error !== null) return 'paused'
  // Without the stream the estimate on screen may be an old one.
  if (!live) return 'connecting…'
  return etaWords(info.ingest.eta_seconds)
}

/** Why a batch can pause: the server takes turns between workspaces. */
export function queueWords(ahead: number): string | null {
  if (ahead === 0) return null
  return `${plural(ahead, 'post', 'posts')} of other workspaces ${ahead === 1 ? 'is' : 'are'} ahead in the queue`
}

/** How fast the embedding model was measured to run on this server. */
export function rateWords(rate: number | null): string | null {
  if (rate === null) return null
  // One decimal under ten posts a second, none when it would be a zero.
  return `The server embeds about ${rate >= 10 ? Math.round(rate) : Number(rate.toFixed(1))} posts a second.`
}

/** When the layout, the topics and their names are computed next. */
export function refreshWords(info: WorkspaceInfo): string | null {
  if (info.refresh.running) return 'refreshing topics…'
  if (info.refresh.next_at === null) return null
  const at = formatCount(info.refresh.next_at)
  // Before the first computation there is no topic yet; afterwards they are only updated.
  return info.refresh.epoch === 0 ? `topics appear at ${at}` : `next refresh at ${at}`
}

/** What the walkthrough says while nothing waits and no post is on the map yet. */
export function waitingLine(info: WorkspaceInfo): string {
  if (info.items === 0) return 'Waiting for the first post…'
  return `${plural(info.items, 'post', 'posts')} received, none long enough to be placed. Send longer texts.`
}

/** A change in the embedding of a workspace worth a line in the log; null when there is none. */
export function ingestChange(before: WorkspaceInfo | null, now: WorkspaceInfo): string | null {
  const was = before?.ingest.error ?? null
  if (now.ingest.error !== null && now.ingest.error !== was) return `embedding is not advancing: ${now.ingest.error}`
  if (now.ingest.error === null && was !== null) return 'embedding is advancing again'
  const waited = before?.pending ?? 0
  if (waited === 0 && now.pending > 0) return `embedding started: ${now.pending} posts wait, ${now.ingest.ahead} of other workspaces ahead`
  if (waited > 0 && now.pending === 0) return `embedding finished: ${now.points} posts placed`
  return null
}
