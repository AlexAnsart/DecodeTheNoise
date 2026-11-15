import type { ReactElement } from 'react'
import { stateWord } from './words'

/** What became of a label's probe: shown, review only, dropped, or not evaluated. */
export function StateChip({ state }: { state: string | null }): ReactElement {
  const word = stateWord(state)
  return (
    <span className={`nm-state nm-state--${state === null ? 'none' : state}`} title={word.meaning || undefined}>
      {word.label}
    </span>
  )
}
