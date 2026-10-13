import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Allow binding to all interfaces when running in Docker
    host: true,
    port: 5173,
  },
})
