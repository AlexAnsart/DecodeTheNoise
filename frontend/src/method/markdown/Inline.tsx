import type { MarkedToken, Token } from 'marked'
import type { ReactElement, ReactNode } from 'react'
import { figureUrl } from '../../api/method'
import type { MarkdownEnv } from './env'
import { decodeEntities, destinationOf, figureOf } from './links'
import { MarkdownLink } from './MarkdownLink'

interface InlineProps {
  tokens: Token[]
  env: MarkdownEnv
}

/** An image of a document. Only the figures of the repository are loaded: a picture on
 *  another site would tell that site who reads the page, so it is left as its words. */
function Picture({ href, alt, env }: { href: string; alt: string; env: MarkdownEnv }): ReactElement {
  const destination = destinationOf(env.base, href)
  const figure = destination.kind === 'path' ? figureOf(destination.path) : null
  if (!figure) return <em>{alt}</em>
  return <img className="nm-md__figure" src={figureUrl(figure)} alt={alt} loading="lazy" />
}

function inline(token: MarkedToken, env: MarkdownEnv, key: number): ReactNode {
  switch (token.type) {
    case 'text':
      return token.tokens ? <Inline key={key} tokens={token.tokens} env={env} /> : decodeEntities(token.text)
    case 'escape':
      return decodeEntities(token.text)
    case 'strong':
      return (
        <strong key={key}>
          <Inline tokens={token.tokens} env={env} />
        </strong>
      )
    case 'em':
      return (
        <em key={key}>
          <Inline tokens={token.tokens} env={env} />
        </em>
      )
    case 'del':
      return (
        <del key={key}>
          <Inline tokens={token.tokens} env={env} />
        </del>
      )
    case 'codespan':
      // Code is literal: what looks like a character reference stays as written.
      return <code key={key}>{token.text}</code>
    case 'br':
      return <br key={key} />
    case 'link':
      return (
        <MarkdownLink key={key} href={token.href} env={env}>
          <Inline tokens={token.tokens} env={env} />
        </MarkdownLink>
      )
    case 'image':
      return <Picture key={key} href={token.href} alt={token.text} env={env} />
    default:
      // Raw HTML and anything unknown is not drawn: a document is text, never markup to run.
      return null
  }
}

/** The inline content of a document: words, emphasis, code, links and figures. */
export function Inline({ tokens, env }: InlineProps): ReactElement {
  return <>{tokens.map((token, index) => inline(token as MarkedToken, env, index))}</>
}
