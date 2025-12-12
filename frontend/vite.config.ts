import { defineConfig } from 'vite'
import path from 'path'
import react from '@vitejs/plugin-react' // keep or remove depending on your stack

export default defineConfig({
  // Option A: serve from `client` dir (recommended if your app entry is in `client`)
  // root: 'client',

  plugins: [react()],
  server: {
    fs: {
      allow: [
        // allow serving files from project root and the client/shared dirs
        path.resolve(__dirname),
        path.resolve(__dirname, 'client'),
        path.resolve(__dirname, 'shared'),
      ],
    },
    proxy: {
      // proxy API REST and websocket requests to backend
      '/api': {
        target: 'http://api:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
      '/health': {
        target: 'http://api:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  resolve: {
    alias: {
      // optional: convenient alias for imports
      '@': path.resolve(__dirname, 'client'),
      '@shared': path.resolve(__dirname, 'shared'),
    },
  },
})
