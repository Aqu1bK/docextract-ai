import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  // Transforms JSX/TSX with the React automatic runtime (React 19).
  // Vitest's esbuild handles TS, but JSX wants the plugin.
  plugins: [react()],
  resolve: {
    alias: {
      // Mirror tsconfig.json's "@/*" → "./*" (paths are relative to apps/web).
      // ESM has no __dirname; the URL form is the portable equivalent.
      '@': fileURLToPath(new URL('.', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['**/*.{test,spec}.{ts,tsx}'],
  },
});
