import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 5173 is Vite's default. If another program already uses it, run with
    //   npm run dev -- --port 5175
    // and open the URL that Vite prints.
    port: 5173,
    // Set to true if you want Vite to open your browser automatically.
    open: false,
  },
  build: {
    // Split the bundle into separate files. Recharts (used for charts) is by far
    // the largest dependency, so giving it its own chunk keeps the initial
    // JavaScript download smaller and the app feeling quicker.
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
        },
      },
    },
    chunkSizeWarningLimit: 700,
  },
})