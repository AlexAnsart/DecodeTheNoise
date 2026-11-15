/* The part of an annotation guide that is about one label. Pure. */

import type { MethodDocument } from '../../api/methodSchema'
import { sectionOfMarkdown } from '../markdown/sections'

export interface GuideExcerpt {
  /** The guide the excerpt is cut from. */
  guide: MethodDocument
  /** The instructions for the label, as written; null when the guide has no heading for it. */
  body: string | null
}

/** A guide names each label in a heading, as code: `call_amplify`. */
function names(label: string): (heading: string) => boolean {
  return (heading) => heading.includes(`\`${label}\``)
}

/** The guide of a label is the guide of its family. When no guide carries that name, any guide
 *  with a heading for the label will do. */
export function guideOf(guides: MethodDocument[], family: string, label: string): GuideExcerpt | null {
  const own = guides.find((guide) => guide.name === family)
  if (own) return { guide: own, body: sectionOfMarkdown(own.markdown, names(label))?.body ?? null }
  for (const guide of guides) {
    const section = sectionOfMarkdown(guide.markdown, names(label))
    if (section) return { guide, body: section.body }
  }
  return null
}
