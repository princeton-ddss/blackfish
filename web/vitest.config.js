import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.{test,spec}.{js,jsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'json-summary'],
      include: ['src/**/*.{js,jsx}'],
      exclude: ['src/test/**', '**/*.{test,spec}.{js,jsx}'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
