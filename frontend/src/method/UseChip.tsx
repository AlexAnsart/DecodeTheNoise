import type { ReactElement } from 'react'
import { purposeWord } from './words'

/** What a label is for: a probe, a descriptor of groups, a test of the LLM review, an aid. */
export function UseChip({ use }: { use: string }): ReactElement {
  const word = purposeWord(use)
  return (
    <span className="nm-state nm-state--use" title={word.meaning || undefined}>
      {word.label}
    </span>
  )
}
