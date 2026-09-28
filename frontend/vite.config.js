import { defineConfig } from 'vite'
export default defineConfig({
  server: { port: 8000, proxy: { '/api': process.env.TW_CLEAN_API_TARGET || 'http://127.0.0.1:5000' } },
  build: { target: 'es2020' }
})
