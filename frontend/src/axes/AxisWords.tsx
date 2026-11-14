import { useImperativeHandle, useRef } from 'react'
import type { ReactElement, Ref } from 'react'
import type { AxisWord } from './axisMarks'
import './axes.css'

export interface AxisWordsHandle {
  /** Moves each word to where its place in the scene falls on the screen. */
  place(project: (position: number[]) => number[]): void
}

interface AxisWordsProps {
  words: AxisWord[]
  ref: Ref<AxisWordsHandle>
}

/** The words of an axis, as HTML over the canvas, placed after each frame. */
export function AxisWords({ words, ref }: AxisWordsProps): ReactElement {
  const nodes = useRef<Array<HTMLSpanElement | null>>([])

  useImperativeHandle(
    ref,
    () => ({
      place(project) {
        words.forEach((word, i) => {
          const node = nodes.current[i]
          if (!node) return
          const [x, y] = project(word.position)
          node.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px) translate(-50%, -50%)`
        })
      },
    }),
    [words],
  )

  return (
    <div className="nm-axis-words" aria-hidden>
      {words.map((word, i) => (
        <span
          // Words are positional: the list is rebuilt whole when the axis changes.
          // eslint-disable-next-line react/no-array-index-key
          key={i}
          ref={(node) => {
            nodes.current[i] = node
          }}
          className={word.title ? 'is-title' : ''}
        >
          {word.text}
        </span>
      ))}
    </div>
  )
}
