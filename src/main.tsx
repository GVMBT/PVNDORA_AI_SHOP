import React from "react";
import ReactDOM from "react-dom/client";
import NewApp from "./NewApp";
import { CartProvider } from "./contexts/CartContext";
import { ErrorBoundary } from "./components/app";
import { AudioEngine } from "./lib/AudioEngine";
import { setupChunkErrorHandler } from "./utils/lazyWithRetry";
import "./index.css";
import type { WebApp } from "./types/telegram";

// Setup global error handler for chunk load failures (stale cache after deploy)
setupChunkErrorHandler();

// Initialize Telegram WebApp
const tgWebApp: WebApp | undefined = window.Telegram?.WebApp;
if (tgWebApp) {
  tgWebApp.ready();
  tgWebApp.expand();

  // Set theme
  document.documentElement.style.setProperty(
    "--tg-theme-bg-color",
    tgWebApp.themeParams.bg_color || "#0a0a0f"
  );
}

// Try to initialize audio ASAP (helps Telegram Mini App autoplay behavior)
// Telegram Mini App sometimes allows AudioContext init right after expand()
try {
  AudioEngine.init();
  void AudioEngine.resume();
} catch {
  // Ignore: some browsers require user gesture; app will still work.
}

// Also listen for first user interaction to unlock audio if needed
const unlockAudio = () => {
  try {
    AudioEngine.init();
    void AudioEngine.resume();
  } catch {
    // Ignore
  }
};

// Add listeners for all possible interaction events
window.addEventListener("pointerdown", unlockAudio, { once: true, passive: true });
window.addEventListener("touchstart", unlockAudio, { once: true, passive: true });
window.addEventListener("click", unlockAudio, { once: true });
window.addEventListener("keydown", unlockAudio, { once: true });

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <CartProvider>
        <NewApp />
      </CartProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
