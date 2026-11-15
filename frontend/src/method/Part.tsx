import type { ReactElement, ReactNode } from 'react'
import type { Request } from '../api/useRequest'

interface PartProps<T> {
  request: Request<T>
  /** What is being read, as the sentences name it: "the dataset", "the evaluation reports". */
  what: string
  children(data: T): ReactNode
}

/** A part of the page that comes from the server: it says that it is loading, that the server
 *  does not publish it yet, or why it failed. It is never a blank. */
export function Part<T>({ request, what, children }: PartProps<T>): ReactElement {
  if (request.status === 'loading') {
    return (
      <p className="nm-note" role="status">
        Reading {what}…
      </p>
    )
  }
  if (request.status === 'error') {
    return request.missing ? <Unpublished what={what} /> : <Failed what={what} message={request.message} />
  }
  return <>{children(request.data)}</>
}

/** The server holds no such part yet. */
export function Unpublished({ what }: { what: string }): ReactElement {
  return <p className="nm-method__empty">Not published yet: this server does not serve {what}.</p>
}

function Failed({ what, message }: { what: string; message: string }): ReactElement {
  const subject = what.charAt(0).toUpperCase() + what.slice(1)
  return (
    <p className="nm-note nm-note--error" role="alert">
      {subject} could not be read. {message}
    </p>
  )
}
