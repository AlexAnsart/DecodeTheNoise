import type { ReactElement } from 'react'
import { CLOSED_ANSWERS, INVALID } from './explorerWords'

interface AnswerProps {
  value: string
  /** Who gave it, said before the answer: a reading, or "settled". */
  by?: string
  title?: string
}

/** An answer on a label: yes, no, unclear, one of the label's own answers, or a yes thrown
 *  away because its quote is not in the post. */
export function Answer({ value, by, title }: AnswerProps): ReactElement {
  const kind = CLOSED_ANSWERS.includes(value) || value === INVALID ? value : 'own'
  const why = value === INVALID ? 'A yes whose quote is not in the post: it counts as no reading.' : title
  return (
    <span className={`nm-answer nm-answer--${kind}`} title={why}>
      {by ? <i>{by}</i> : null}
      {value}
    </span>
  )
}
