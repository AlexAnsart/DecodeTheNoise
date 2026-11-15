import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import { initTheme } from './theme/theme'
import './theme/tokens.css'
import './theme/base.css'
// Last: it overrides the stylesheets of the features, which come in with the app.
import './theme/small-screens.css'

initTheme()

const root = document.getElementById('root')
if (!root) throw new Error('The page has no root element.')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
