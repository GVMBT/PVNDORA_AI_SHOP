import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import NewApp from './NewApp'
import './index.css'

// Feature flag for new UI
// Enable via URL param: ?new_ui=1 or localStorage: localStorage.setItem('pvndora_new_ui', '1')
const useNewUI = () => {
  // Check URL param
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.get('new_ui') === '1') {
    localStorage.setItem('pvndora_new_ui', '1')
    return true
  }
  if (urlParams.get('new_ui') === '0') {
    localStorage.removeItem('pvndora_new_ui')
    return false
  }
  // Check localStorage
  return localStorage.getItem('pvndora_new_ui') === '1'
}

// Initialize Telegram WebApp
if (window.Telegram?.WebApp) {
  window.Telegram.WebApp.ready()
  window.Telegram.WebApp.expand()
  
  // Set theme
  document.documentElement.style.setProperty(
    '--tg-theme-bg-color',
    window.Telegram.WebApp.themeParams.bg_color || '#0a0a0f'
  )
}

const AppComponent = useNewUI() ? NewApp : App

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppComponent />
  </React.StrictMode>,
)
