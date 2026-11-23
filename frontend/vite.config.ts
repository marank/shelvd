import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'
import basicSsl from '@vitejs/plugin-basic-ssl'

// The repo's .env (shared with Django, see .env.example); real env vars win. Read here
// rather than in a config callback because vitest.config.ts merges this object.
const env = loadEnv(
  process.env.NODE_ENV ?? 'development',
  fileURLToPath(new URL('..', import.meta.url)),
  '',
)
const backend = env.VITE_BACKEND_URL || `http://127.0.0.1:${env.BACKEND_PORT || '8000'}`
// DEV_HTTPS=true: self-signed https, so phones in the LAN may use the camera (scanner).
const https = env.DEV_HTTPS === 'true'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools(), tailwindcss(), ...(https ? [basicSsl()] : [])],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // Same port as the Docker stack (APP_PORT); backend/config/settings.py allows it for
    // CSRF in DEBUG.
    port: Number(env.APP_PORT || '8080'),
    strictPort: true,
    // Same origin as in Docker: Django must see the browser's Host for CSRF, so no
    // changeOrigin.
    proxy: {
      '/api': { target: backend },
      '/admin': { target: backend },
      '/django-static': { target: backend },
      '/media': { target: backend },
    },
  },
})
