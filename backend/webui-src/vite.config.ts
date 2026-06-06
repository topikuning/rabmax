import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

// Build → static (di-serve FastAPI). Dev → proxy /api & /files ke backend :8000.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/files': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
