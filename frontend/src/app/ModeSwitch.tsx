import { Database, Radio } from 'lucide-react'
import type { ReactElement } from 'react'
import type { Page } from '../route/useRoute'
import { PATHS, navigate } from '../route/useRoute'

const MODES = [
  { page: 'demo', label: 'Demo dataset', short: 'Demo', icon: Database, title: 'A public sample dataset, ready to explore' },
  { page: 'workspace', label: 'My workspace', short: 'Workspace', icon: Radio, title: 'Your own posts, sent through the API' },
] as const

/** The two maps of the app, always one click apart. */
export function ModeSwitch({ page }: { page: Page }): ReactElement {
  return (
    <div className="nm-segmented nm-mode" role="group" aria-label="Which map is shown" data-tour="mode">
      {MODES.map(({ page: mode, label, short, icon: Icon, title }) => (
        <button
          key={mode}
          type="button"
          className={page === mode ? 'is-active' : ''}
          aria-pressed={page === mode}
          title={title}
          onClick={() => navigate(PATHS[mode])}
        >
          <Icon size={13} aria-hidden />
          {/* One of the two is shown, by the width of the window (theme/small-screens.css). */}
          <span className="nm-mode__long">{label}</span>
          <span className="nm-mode__short">{short}</span>
        </button>
      ))}
    </div>
  )
}
