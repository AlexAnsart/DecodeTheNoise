import type { ReactElement } from 'react'
import type { Method } from '../../api/methodSchema'
import { plural } from '../../text/format'
import { Disclosure } from '../Disclosure'
import type { Reports } from '../reports'
import { SourceLink } from '../SourceLink'
import { ReviewEvaluation } from './ReviewEvaluation'
import { NEVER, WHEN, selectionLine, stepsOf } from './reviewSteps'
import './review.css'

interface ReviewSectionProps {
  method: Method
  reports: Reports
}

/** The LLM review as it runs: when, how, the exact prompts, the techniques it screens, and
 *  what its evaluation against the annotation measured. */
export function ReviewSection({ method, reports }: ReviewSectionProps): ReactElement {
  const { review } = method
  if (!review) return <p className="nm-method__empty">Not published yet: no LLM review runs on this server, so there is no prompt to show.</p>
  const selection = selectionLine(review)
  return (
    <>
      <dl className="nm-facts nm-facts--wide">
        <div>
          <dt>Model</dt>
          <dd className="nm-num">{review.model ?? 'None set up on this server: nothing is reviewed.'}</dd>
        </div>
        <div>
          <dt>Prompt of one post</dt>
          <dd className="nm-num">{review.prompt_version}</dd>
        </div>
        <div>
          <dt>Prompt of a selection</dt>
          <dd className="nm-num">{review.selection_prompt_version}</dd>
        </div>
        <div>
          <dt>Code</dt>
          <dd>
            <SourceLink path="backend/review/" />
          </dd>
        </div>
      </dl>
      <div className="nm-two">
        <div>
          <h3>When it runs</h3>
          <ul>
            {WHEN.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>What it never says</h3>
          <p>{NEVER}</p>
        </div>
      </div>
      <h3>What it does, step by step</h3>
      <ol className="nm-steps-list">
        {stepsOf(review).map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      {selection ? <p>{selection}</p> : null}
      <Disclosure title="The techniques it screens every post for" hint={plural(review.techniques.length, 'technique', 'techniques')}>
        {review.techniques.length > 0 ? (
          <dl className="nm-techniques">
            {review.techniques.map((technique) => (
              <div key={technique.key}>
                <dt>
                  {technique.name}
                  <code>{technique.key}</code>
                </dt>
                <dd>{technique.question ?? 'Its question was not published.'}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="nm-method__empty">The review screens for no technique on this server: its technique guides are not loaded.</p>
        )}
      </Disclosure>
      <Disclosure title="The exact system prompt, for one post" hint={review.prompt_version}>
        <pre className="nm-prompt" tabIndex={0}>
          {review.system}
        </pre>
      </Disclosure>
      <Disclosure title="The exact system prompt, for a selection" hint={review.selection_prompt_version}>
        <pre className="nm-prompt" tabIndex={0}>
          {review.selection_system}
        </pre>
      </Disclosure>
      <h3>How it was measured</h3>
      <ReviewEvaluation report={reports.review} techniques={review.techniques} />
    </>
  )
}
