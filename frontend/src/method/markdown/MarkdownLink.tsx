import type { ReactElement, ReactNode } from 'react'
import type { Target } from '../hash'
import { sourceUrl, useMethodShared } from '../MethodContext'
import type { MarkdownEnv } from './env'
import { destinationOf, figureOf } from './links'

interface MarkdownLinkProps {
  href: string
  env: MarkdownEnv
  children: ReactNode
}

/** A path that the page can show itself: one of its documents, a guide, a figure. */
function placeOf(path: string, guides: { name: string; path: string }[], documents: { name: string; path: string }[]): Target | null {
  const guide = guides.find((doc) => doc.path === path)
  if (guide) return { kind: 'guide', name: guide.name }
  const document = documents.find((doc) => doc.path === path)
  if (document) return { kind: 'doc', name: document.name }
  const figure = figureOf(path)
  if (figure) return { kind: 'figure', name: figure }
  // The folder of the guides is the list of the guides.
  if (guides.length > 0 && guides.every((doc) => doc.path.startsWith(path)) && path.endsWith('/')) return { kind: 'section', section: 'labels' }
  return null
}

/** A link of a document. A neighbour document opens in the page; any other path of the
 *  repository opens at the deployed commit; another site opens in a new tab. */
export function MarkdownLink({ href, env, children }: MarkdownLinkProps): ReactElement {
  const { nav, source, guides, documents } = useMethodShared()
  const destination = destinationOf(env.base, href)
  if (destination.kind === 'web') {
    return (
      <a className="nm-link" href={destination.url} target="_blank" rel="noopener noreferrer nofollow">
        {children}
      </a>
    )
  }
  if (destination.kind === 'anchor') {
    const id = `${env.ids}-${destination.id}`
    return (
      <a
        className="nm-link"
        href={`#${id}`}
        onClick={(event) => {
          // The address holds what is open in the page: a heading is reached without changing it.
          event.preventDefault()
          document.getElementById(id)?.scrollIntoView({ block: 'start' })
        }}
      >
        {children}
      </a>
    )
  }
  if (destination.kind === 'path') {
    const place = placeOf(destination.path, guides, documents)
    if (place) {
      return (
        <a
          className="nm-link"
          href={nav.href(place)}
          onClick={(event) => {
            event.preventDefault()
            nav.go(place)
          }}
        >
          {children}
        </a>
      )
    }
    const url = sourceUrl(source, destination.path)
    if (url) {
      return (
        <a className="nm-link" href={url} target="_blank" rel="noopener noreferrer" title={`${destination.path} at the deployed commit`}>
          {children}
        </a>
      )
    }
  }
  return <>{children}</>
}
