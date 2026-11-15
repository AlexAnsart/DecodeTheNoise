import type { MarkedToken, Token, Tokens } from 'marked'
import { createElement } from 'react'
import type { ReactElement, ReactNode } from 'react'
import type { MarkdownEnv } from './env'
import { Inline } from './Inline'
import { slug } from './links'

interface BlocksProps {
  tokens: Token[]
  env: MarkdownEnv
}

function Table({ token, env }: { token: Tokens.Table; env: MarkdownEnv }): ReactElement {
  const align = (index: number): { textAlign: 'left' | 'right' | 'center' } | undefined => {
    const side = token.align[index]
    return side ? { textAlign: side } : undefined
  }
  return (
    <div className="nm-table-wrap">
      <table className="nm-table">
        <thead>
          <tr>
            {token.header.map((cell, index) => (
              <th key={index} scope="col" style={align(index)}>
                <Inline tokens={cell.tokens} env={env} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {token.rows.map((row, at) => (
            <tr key={at}>
              {row.map((cell, index) => (
                <td key={index} style={align(index)}>
                  <Inline tokens={cell.tokens} env={env} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function List({ token, env }: { token: Tokens.List; env: MarkdownEnv }): ReactElement {
  const items = token.items.map((item, index) => (
    <li key={index}>
      <Blocks tokens={item.tokens} env={env} />
    </li>
  ))
  return token.ordered ? <ol start={token.start === '' ? undefined : token.start}>{items}</ol> : <ul>{items}</ul>
}

function block(token: MarkedToken, env: MarkdownEnv, key: number): ReactNode {
  switch (token.type) {
    case 'heading': {
      const level = Math.min(6, token.depth + env.shift)
      const children = <Inline tokens={token.tokens} env={env} />
      return createElement(`h${level}`, { key, id: `${env.ids}-${slug(token.text)}`, className: `nm-md__h${token.depth}` }, children)
    }
    case 'paragraph':
      return (
        <p key={key}>
          <Inline tokens={token.tokens} env={env} />
        </p>
      )
    case 'text':
      // The line of a tight list item: words without a paragraph around them.
      return <Inline key={key} tokens={token.tokens ?? [token]} env={env} />
    case 'list':
      return <List key={key} token={token} env={env} />
    case 'table':
      return <Table key={key} token={token} env={env} />
    case 'code':
      return (
        <pre key={key} className="nm-md__code" tabIndex={0}>
          <code>{token.text}</code>
        </pre>
      )
    case 'blockquote':
      return (
        <blockquote key={key}>
          <Blocks tokens={token.tokens} env={env} />
        </blockquote>
      )
    case 'hr':
      return <hr key={key} />
    default:
      // Blank lines, link definitions and raw HTML: nothing to draw.
      return null
  }
}

/** The blocks of a document: headings, paragraphs, lists, tables, code. */
export function Blocks({ tokens, env }: BlocksProps): ReactElement {
  return <>{tokens.map((token, index) => block(token as MarkedToken, env, index))}</>
}
