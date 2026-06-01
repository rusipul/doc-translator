import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/translate': 'http://localhost:8000',
      '/settings': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
