/**
 * main.jsx - the entry point React runs first.
 *
 * It mounts <App /> into the #root element defined in index.html.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

const container = document.getElementById('root')

if (!container) {
  throw new Error('Could not find the #root element in index.html')
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>
)