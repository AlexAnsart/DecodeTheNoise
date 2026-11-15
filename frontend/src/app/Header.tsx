import { BookOpen, CircleHelp, CodeXml, Moon, Plug, Settings, Sun } from 'lucide-react'
import type { ReactElement } from 'react'
import { Link } from '../route/Link'
import type { Page } from '../route/useRoute'
import { PATHS } from '../route/useRoute'
import { useTheme } from '../theme/theme'
import type { WorkspacePanel } from '../workspace/panel'
import { ModeSwitch } from './ModeSwitch'

const SOURCE_URL = 'https://github.com/AlexAnsart/DecodeTheNoise'

interface HeaderProps {
  page: Page
  /** This browser holds the key of a workspace: its panels can be opened. */
  workspaceOpen: boolean
  onPanel(panel: WorkspacePanel): void
  onTour(): void
}

/** The bar every page shares: which map is shown, and the ways out of it. */
export function Header({ page, workspaceOpen, onPanel, onTour }: HeaderProps): ReactElement {
  const [theme, toggleTheme] = useTheme()
  const otherTheme = theme === 'dark' ? 'Switch to the light theme' : 'Switch to the dark theme'
  return (
    <header className="nm-header">
      <div className="nm-header__left">
        <Link to={PATHS.demo} className="nm-brand" title="NoiseMap">
          <span className="nm-brand__mark" aria-hidden>
            <i />
            <i />
            <i />
          </span>
          <strong>NoiseMap</strong>
        </Link>
        <ModeSwitch page={page} />
        <span className="nm-brand__line">Every post becomes a point on a meaning map.</span>
      </div>
      <nav className="nm-header__nav" aria-label="Pages and tools">
        {page === 'workspace' && workspaceOpen ? (
          <>
            <button type="button" className="nm-tool" onClick={() => onPanel('connect')} title="Your API key and the ways to send posts">
              <Plug size={13} aria-hidden />
              Connect
            </button>
            <button type="button" className="nm-tool nm-tool--icon" onClick={() => onPanel('settings')} title="Workspace settings" aria-label="Workspace settings">
              <Settings size={15} aria-hidden />
            </button>
          </>
        ) : null}
        <Link to={PATHS.method} className={`nm-tool nm-header__method${page === 'method' ? ' is-active' : ''}`} title="How it works, the scores of every probe, and the posts and guides behind them">
          <BookOpen size={13} aria-hidden />
          Method and scores
        </Link>
        <button type="button" className="nm-tool nm-tool--icon" onClick={onTour} title="Take the tour of the map" aria-label="Take the tour of the map">
          <CircleHelp size={15} aria-hidden />
        </button>
        <a className="nm-tool nm-header__source" href={SOURCE_URL} target="_blank" rel="noopener noreferrer" title="The source code, on GitHub">
          <CodeXml size={13} aria-hidden />
          Source
        </a>
        <button type="button" className="nm-tool nm-tool--icon" onClick={toggleTheme} title={otherTheme} aria-label={otherTheme}>
          {theme === 'dark' ? <Sun size={15} aria-hidden /> : <Moon size={15} aria-hidden />}
        </button>
      </nav>
    </header>
  )
}
