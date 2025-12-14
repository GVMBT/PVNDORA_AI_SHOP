import React from 'react';
import ReactDOM from 'react-dom/client';
import NewApp from './NewApp';
import { CartProvider } from './contexts/CartContext';
import { ErrorBoundary } from './components/app';
import './index.css';

// Telegram WebApp type declaration
declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        themeParams: {
          bg_color?: string;
        };
        initData?: string;
        initDataUnsafe?: {
          user?: {
            id: number;
            language_code?: string;
          };
          start_param?: string;
        };
      };
    };
  }
}

// Initialize Telegram WebApp
if (window.Telegram?.WebApp) {
  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand();
  
  // Set theme
  document.documentElement.style.setProperty(
    '--tg-theme-bg-color',
    window.Telegram.WebApp.themeParams.bg_color || '#0a0a0f'
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
