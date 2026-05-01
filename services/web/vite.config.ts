import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  server: { port: 30000 },
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
})
