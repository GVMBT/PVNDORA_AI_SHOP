import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'es2020',
    minify: 'esbuild',
    // Removed manualChunks to prevent build errors when dependencies are removed
    // Vite will automatically optimize chunks
    chunkSizeWarningLimit: 600
  },
  esbuild: {
    drop: ['console', 'debugger']
  }
})
