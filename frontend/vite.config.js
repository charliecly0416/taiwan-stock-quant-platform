import { defineConfig } from 'vite'
export default defineConfig({
  server: { port: 8000, proxy: { '/api': 'http://127.0.0.1:5000' } },
  build: { target: 'es2020' }
})
