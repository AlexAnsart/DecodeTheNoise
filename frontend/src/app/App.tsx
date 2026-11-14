import { useState } from 'react'
import type { ReactElement } from 'react'
import { MethodPage } from '../method/MethodPage'
import { PATHS, navigate, useInternalLinks, useRoute } from '../route/useRoute'
import { useTour } from '../tour/useTour'
import type { WorkspacePanel } from '../workspace/panel'
import { useStoredWorkspace } from '../workspace/storedKey'
import { WorkspacePage } from '../workspace/WorkspacePage'
import { DemoPage } from './DemoPage'
import { Header } from './Header'
import './app.css'

/** The shell: one header, then the demo map, the visitor's own workspace, or the method page. */
export function App(): ReactElement {
  const page = useRoute()
  useInternalLinks()
  const tour = useTour()
  const stored = useStoredWorkspace()
  const [panel, setPanel] = useState<WorkspacePanel | null>(null)
  // A panel belongs to the page it was opened on: leaving the page closes it.
  const [panelPage, setPanelPage] = useState(page)
  if (panelPage !== page) {
    setPanelPage(page)
    setPanel(null)
  }

  const startTour = (): void => {
    navigate(PATHS.demo)
    tour.start()
  }

  return (
    <div className="nm-app">
      <Header page={page} workspaceOpen={stored !== null} onPanel={setPanel} onTour={startTour} />
      <main className="nm-main">
        {page === 'demo' ? <DemoPage tour={tour} /> : null}
        {page === 'workspace' ? <WorkspacePage panel={panel} onPanel={setPanel} /> : null}
        {page === 'method' ? <MethodPage /> : null}
      </main>
    </div>
  )
}
