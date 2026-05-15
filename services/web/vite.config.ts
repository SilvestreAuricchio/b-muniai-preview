import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 30000,
    proxy: {
      '/bff': { target: 'http://localhost:30001', changeOrigin: true },
    },
  },
  preview: { port: 30000, host: '0.0.0.0', allowedHosts: ['muninai.com.aw'] },
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
})
