import { defineConfig } from 'vite';
import path from 'node:path';

export default defineConfig({
  root: path.resolve(__dirname, 'static_src'),
  base: '/static/build/',
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    origin: 'http://localhost:5173'
  },
  build: {
    manifest: 'manifest.json',
    outDir: path.resolve(__dirname, 'static/build'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'static_src/js/main.js'),
        styles: path.resolve(__dirname, 'static_src/css/main.css')
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'static_src')
    }
  }
});

