import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// If VITE_API is not set, we proxy certain paths to the default backend
const backendTarget = process.env.VITE_API || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Allow using relative fetches like /media/upload in dev without setting VITE_API
      '/media': { target: backendTarget, changeOrigin: true },
      '/auth': { target: backendTarget, changeOrigin: true },
      '/realtime': { target: backendTarget, ws: true, changeOrigin: true }
    }
  }
});
