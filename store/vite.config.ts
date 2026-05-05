import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5174,
    proxy: {
      // Dev 直接打 Railway production backend（與 vercel.json rewrite 同源）
      // 切回本機 backend：改回 'http://localhost:8001'
      '/api': {
        target: 'https://paint-web-production.up.railway.app',
        changeOrigin: true,
        secure: true,
      },
    },
  },
})
