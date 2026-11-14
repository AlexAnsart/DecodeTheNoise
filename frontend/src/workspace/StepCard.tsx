import type { ReactElement, ReactNode } from 'react'

interface StepCardProps {
  step: number
  title: string
  children: ReactNode
}

/** One numbered step of the walkthrough: a title, then the one thing to do. */
export function StepCard({ step, title, children }: StepCardProps): ReactElement {
  return (
    <section className="nm-step" aria-label={`Step ${step}: ${title}`}>
      <header className="nm-step__head">
        <span className="nm-step__number" aria-hidden>
          {step}
        </span>
        <h2>{title}</h2>
      </header>
      <div className="nm-step__body">{children}</div>
    </section>
  )
}
