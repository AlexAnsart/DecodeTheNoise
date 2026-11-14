import { ScanSearch } from 'lucide-react'
import type { ReactElement, ReactNode } from 'react'
import type { Confidence } from '../api/schema'
import './verdict.css'

interface VerdictBlockProps {
  /** What the detector looks for, never stated as a fact about the item. */
  label: string
  confidence: Confidence
  /** What was found, in one sentence. */
  evidence: string
  /** The measured reliability of the detector, one line per rate. */
  measured: string[]
  /** The ways further: the evidence in full, the evaluation report. */
  children: ReactNode
}

/** A verdict as the product always shows it: the level of confidence, what was found, and how
 *  reliable the detector measured to be. Never a score alone. */
export function VerdictBlock({ label, confidence, evidence, measured, children }: VerdictBlockProps): ReactElement {
  return (
    <section className={`nm-verdict nm-verdict--${confidence}`} aria-label={`${label}: ${confidence}`}>
      <header className="nm-verdict__head">
        <ScanSearch size={13} aria-hidden />
        <strong>{label}</strong>
        <span className="nm-verdict__level">{confidence}</span>
      </header>
      <p className="nm-verdict__evidence">{evidence}</p>
      {measured.length > 0 ? (
        <ul className="nm-verdict__measured">
          {measured.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
      <div className="nm-verdict__actions">{children}</div>
    </section>
  )
}
