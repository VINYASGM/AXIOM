import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
    },
    plugins: [react()],
    define: {
      // SECURITY: API keys must NOT be bundled into client code.
      // Use server-side proxy (/api/gemini/*) instead.
      // TODO: Build backend proxy for Gemini API calls
      'process.env.API_URL': JSON.stringify(env.VITE_API_URL || 'http://localhost:8080')
    },
    test: {
      environment: 'jsdom',
      globals: true,
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
        'react': path.resolve(__dirname, '../../node_modules/react'),
        'react-dom': path.resolve(__dirname, '../../node_modules/react-dom'),
      }
    }
  };
});
