import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite dev server proxies /predict straight through to your Flask app,
// so the browser never hits a cross-origin request and app.py needs
// zero changes. Adjust the target if Flask runs on a different port.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/predict': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
