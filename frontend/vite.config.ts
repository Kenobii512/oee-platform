/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend (FastAPI) varsayılan portu. Dev'de API istekleri buraya proxy'lenir (CORS'suz).
const BACKEND = 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/oee': BACKEND,
      '/loss-tree': BACKEND,
      '/recommendations': BACKEND,
      '/data-quality': BACKEND,
      '/scenarios': BACKEND,
      '/replay': BACKEND,
      '/ingest': BACKEND,
      '/health': BACKEND,
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
})
