import { Moon, Sun } from 'lucide-react'
import type { ReactElement } from 'react'
import { MapScreen } from '../map/MapScreen'
import { useTheme } from '../theme/theme'
import { SOURCE_URL } from './source'
import './app.css'

export function App(): ReactElement {
  const [theme, toggleTheme] = useTheme()
  return (
    <div className="nm-app">
      <header className="nm-header">
        <div className="nm-brand">
          <span className="nm-brand__mark" aria-hidden>
            <i />
            <i />
            <i />
          </span>
          <strong>NoiseMap</strong>
          <span className="nm-brand__line">Every post becomes a point on a meaning map.</span>
        </div>
        <nav className="nm-header__nav">
          <a href={SOURCE_URL} target="_blank" rel="noopener noreferrer">
            Source
          </a>
          <button
            type="button"
            className="nm-tool nm-tool--icon"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Switch to the light theme' : 'Switch to the dark theme'}
            aria-label={theme === 'dark' ? 'Switch to the light theme' : 'Switch to the dark theme'}
          >
            {theme === 'dark' ? <Sun size={15} aria-hidden /> : <Moon size={15} aria-hidden />}
          </button>
        </nav>
      </header>
      <main className="nm-main">
        <MapScreen />
      </main>
    </div>
  )
}
