import { marked } from 'marked'
import { useMemo } from 'react'
import type { ReactElement } from 'react'
import { Blocks } from './Blocks'
import type { MarkdownEnv } from './env'
import './markdown.css'

interface MarkdownProps {
  source: string
  /** Path of the document in the repository. */
  base: string
  /** Prefix of the heading ids. */
  ids: string
  shift?: number
}

/** A document of the repository, drawn from its markdown. The text is read into tokens and
 *  each token becomes an element: no HTML of the document is ever inserted in the page. */
export function Markdown({ source, base, ids, shift = 1 }: MarkdownProps): ReactElement {
  const tokens = useMemo(() => marked.lexer(source), [source])
  const env = useMemo<MarkdownEnv>(() => ({ base, ids, shift }), [base, ids, shift])
  return (
    <div className="nm-md">
      <Blocks tokens={tokens} env={env} />
    </div>
  )
}
