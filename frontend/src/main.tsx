import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import { initTheme } from './theme/theme'
import './theme/tokens.css'
import './theme/base.css'

initTheme()

const root = document.getElementById('root')
if (!root) throw new Error('The page has no root element.')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
