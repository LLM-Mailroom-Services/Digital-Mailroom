import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Production builds live under /desk on the visualizer. `npm run dev`
// uses `/` and proxies /api /v1 /ws to mailroom-web (:8001).
const production = process.env.NODE_ENV === 'production'

export default defineConfig({
  base: process.env.VITE_BASE || (production ? '/desk/' : '/'),
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/v1': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8001',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    emptyOutDir: true,
  },
})
