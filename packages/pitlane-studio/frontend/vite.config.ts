import { defineConfig } from 'vite'
import { sveltekit } from '@sveltejs/kit/vite'

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 5173,
    proxy: {
      '/articles': { target: 'http://localhost:8001', changeOrigin: false },
      '/acts':      { target: 'http://localhost:8001', changeOrigin: false },
      '/races':     { target: 'http://localhost:8001', changeOrigin: false },
    },
  },
})
