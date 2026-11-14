import { TriangleAlert } from 'lucide-react'
import type { ReactElement } from 'react'
import './ingest.css'

/** Why embedding is not advancing, in the server's own words. It stays on screen for as long
 *  as the server says so: the server keeps the posts and tries again by itself. */
export function IngestWarning({ message }: { message: string }): ReactElement {
  return (
    <div className="nm-ingest-warning" role="alert">
      <TriangleAlert size={13} aria-hidden />
      <span>{message}</span>
    </div>
  )
}
