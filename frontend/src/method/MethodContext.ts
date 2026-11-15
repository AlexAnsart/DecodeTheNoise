/* What every part of the method page shares: how to move in it, and where the source of the
   deployed version is, so that any path of the repository can be linked. */

import { createContext, useContext } from 'react'
import type { MethodDocument } from '../api/methodSchema'
import type { MethodNav } from './useMethodNav'

export interface MethodShared {
  nav: MethodNav
  /** Repository and commit of what is deployed; null while the server has not said. */
  source: { repository: string; commit: string } | null
  /** The documents that can be read in the page: a link to one of their paths opens it here. */
  guides: MethodDocument[]
  documents: MethodDocument[]
}

export const MethodContext = createContext<MethodShared | null>(null)

export function useMethodShared(): MethodShared {
  const shared = useContext(MethodContext)
  if (!shared) throw new Error('A part of the method page was rendered outside the page.')
  return shared
}

/** The address of a file or a folder of the repository, at the commit that is deployed. */
export function sourceUrl(source: MethodShared['source'], path: string): string | null {
  if (!source) return null
  const clean = path.replace(/^\.?\/+/, '')
  // A folder is browsed, a file is read.
  const view = clean.endsWith('/') || !/\.[a-z0-9]+$/i.test(clean) ? 'tree' : 'blob'
  return `${source.repository.replace(/\/+$/, '')}/${view}/${source.commit}/${clean.replace(/\/+$/, '')}`
}
