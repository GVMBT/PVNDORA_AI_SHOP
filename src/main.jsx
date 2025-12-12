import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import NewApp from './NewApp'
import './index.css'

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

// Always render new UI
const AppComponent = NewApp

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppComponent />
  </React.StrictMode>,
)
