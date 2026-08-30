import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    // Mirrors nginx.conf's /api/ proxy so `npm run dev` talks to the local
    // backend without needing VITE_API_URL set.
    proxy: {
      '/api': 'http://localhost:8001',
      '/uploads': 'http://localhost:8001',
    },
  },
  build: {
    outDir: 'dist',
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
