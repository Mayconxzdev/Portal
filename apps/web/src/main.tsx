import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { GlobalErrorBoundary } from './components/ui/GlobalErrorBoundary'
import './styles/tokens.css'
import './styles/index.css'
import './styles/utility-compat.css'
import './styles/module-pages.css'
import './styles/kanban-module.css'
import './styles/chat-module.css'
import './styles/approvals-module.css'
import './styles/admin-module.css'
import './styles/purchases-module.css'
import './styles/automations-module.css'
import './styles/stock-catalog.css'


const nativeFetch = window.fetch.bind(window)

window.fetch = (input: RequestInfo | URL, init: RequestInit = {}) => {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
  const shouldSendSessionCookie = url.includes('/api/')

  return nativeFetch(input, {
    ...init,
    credentials: init.credentials ?? (shouldSendSessionCookie ? 'same-origin' : undefined),
  })
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GlobalErrorBoundary>
      <App />
    </GlobalErrorBoundary>
  </React.StrictMode>,
)
