import { FileCode } from 'lucide-react'
import type { ReactElement } from 'react'
import { sourceUrl, useMethodShared } from './MethodContext'

/** A file or a folder of the repository, linked at the commit that is deployed: what produced
 *  a number can be read as it was when the number was produced. */
export function SourceLink({ path }: { path: string }): ReactElement {
  const { source } = useMethodShared()
  const url = sourceUrl(source, path)
  if (!url) return <code className="nm-source">{path}</code>
  return (
    <a className="nm-source" href={url} target="_blank" rel="noopener noreferrer" title={`${path} at commit ${source?.commit.slice(0, 12)}`}>
      <FileCode size={12} aria-hidden />
      {path}
    </a>
  )
}
