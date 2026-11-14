import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // In development the API runs beside the dev server; in production the proxy routes /api.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
