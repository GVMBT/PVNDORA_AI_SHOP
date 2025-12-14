import React from 'react';
import ReactDOM from 'react-dom/client';
import NewApp from './NewApp';
import { CartProvider } from './contexts/CartContext';
import { ErrorBoundary } from './components/app';
import './index.css';
import type { WebApp } from './types/telegram';

// Initialize Telegram WebApp
const tgWebApp: WebApp | undefined = window.Telegram?.WebApp;
if (tgWebApp) {
  tgWebApp.ready();
  tgWebApp.expand();
  
  // Set theme
  document.documentElement.style.setProperty(
    '--tg-theme-bg-color',
    tgWebApp.themeParams.bg_color || '#0a0a0f'
  );
}

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <CartProvider>
        <NewApp />
      </CartProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
