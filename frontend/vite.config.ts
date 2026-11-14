/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const API_TARGET = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.VITE_API_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: API_TARGET, changeOrigin: true } },
  },
  preview: {
    port: 4173,
    proxy: { '/api': { target: API_TARGET, changeOrigin: true } },
  },
  build: {
    target: 'es2022',
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: { recharts: ['recharts'], react: ['react', 'react-dom'] },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: false,
    include: ['tests/**/*.test.{ts,tsx}'],
    css: false,
  },
});
