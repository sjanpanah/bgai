import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Defaults to the host-local backend; docker-compose overrides this to the
// "api" service name since the dev server proxies from inside its container.
const apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    proxy: {
      '/game': apiTarget,
      '/engines': apiTarget,
      '/engine': apiTarget,
    },
  },
})
