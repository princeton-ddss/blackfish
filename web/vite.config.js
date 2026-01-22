 import { defineConfig } from 'vite';
 import react from '@vitejs/plugin-react';
 import path from 'path';

 export default defineConfig({
   plugins: [react()],
   base: './',  // CRITICAL: relative paths for OOD
   resolve: {
     alias: { '@': path.resolve(__dirname, './src') },
   },
   build: {
     outDir: 'build',
     assetsDir: 'assets',
   },
   server: {
     port: 3000,
     proxy: { '/api': 'http://localhost:8000' },
   },
 });
