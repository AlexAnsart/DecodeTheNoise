/* What each figure shows, as the documents that include it say. Pure. */

import type { MethodDocument } from '../../api/methodSchema'

const IMAGE = /!\[([^\]]*)\]\(([^)\s]+)[^)]*\)/g

export interface FigureUse {
  caption: string
  /** The document that shows the figure. */
  document: string
}

/** Figure file name to its caption and its document: the first document that includes it. */
export function figureUses(documents: MethodDocument[]): Map<string, FigureUse> {
  const uses = new Map<string, FigureUse>()
  for (const document of documents) {
    for (const [, caption, href] of document.markdown.matchAll(IMAGE)) {
      const name = href.split('/').pop()
      if (name && !uses.has(name)) uses.set(name, { caption, document: document.name })
    }
  }
  return uses
}
